from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from .config import get_settings
from .db import engine, get_db
from .models import (
    AgentRun, AgentRunAttempt, AgentRunTransition, Approval, AuditLog, Commitment,
    Handoff, KnowledgeItem, LeadStub, ManualTask, MemoryEntry, OrganizationEvent,
    MarketingCase, Outbox, Role, SalesFeedback,
)
from .policy import canonical_hash, find_idempotent, prepare_write, record_write
from .observability import configure_observability, current_trace_headers, metrics
from .model_admin import (
    LocalModelConfigRequest, configure_model, execution_enabled, require_local_admin, status_payload,
)
from .schemas import (
    ApprovalCreate, CommitmentCreate, CommitmentTransition, EventCreate, HandoffCreate,
    KnowledgeCreate, LeadStubCreate, ManualTaskCreate, ManualTaskReceipt,
    MarketingCaseCommand, MarketingCaseCreate, MemoryCreate, RunCreate, SalesFeedbackCreate,
)
from .security import Actor, current_actor, require_any
from .run_state import append_transition, request_cancellation
from .marketing_case import (
    MarketingCaseConflict, case_snapshot, create_marketing_case, execute_case_command,
)


ROLE_SEEDS = [
    ("DROLE-01", "产品营销 Agent", "pma", "product_marketing_owner"),
    ("DROLE-02", "品牌与增长 Agent", "bga", "brand_growth_owner"),
    ("DROLE-03", "营销协同 Agent", "mo", "brand_growth_owner"),
]

log = logging.getLogger("1cat.runtime.api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    from .db import SessionLocal

    with SessionLocal() as db:
        for role_id, name, profile, owner in ROLE_SEEDS:
            if not db.get(Role, role_id):
                manifest = {
                    "role_id": role_id, "name": name, "profile_id": profile,
                    "owner_role": owner, "r0": "human-supervised",
                }
                db.add(Role(id=role_id, name=name, profile_id=profile, owner_role=owner,
                            lifecycle="onboarding", manifest=manifest, content_hash=canonical_hash(manifest)))
        db.commit()
    yield


app = FastAPI(title="1Cat Hermes OS Runtime", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
configure_observability(service_name="1cat-runtime-api", app=app, engine=engine)


def as_dict(obj):
    return {
        attribute.columns[0].name: getattr(obj, attribute.key)
        for attribute in inspect(obj).mapper.column_attrs
    }


def attempt_dict(attempt: AgentRunAttempt) -> dict:
    """Return browser-safe Attempt evidence without exposing the fencing token."""
    result = as_dict(attempt)
    result.pop("lease_token", None)
    return result


def trace_id_from_traceparent(value: str | None) -> str | None:
    if not value:
        return None
    parts = value.strip().split("-")
    if len(parts) != 4 or len(parts[1]) != 32 or parts[1] == "0" * 32:
        return None
    try:
        int(parts[1], 16)
    except ValueError:
        return None
    return parts[1].lower()


def run_dict(db: Session, item: AgentRun, *, include_attempt: bool = False):
    result = as_dict(item)
    result["trace_id"] = trace_id_from_traceparent(item.traceparent)
    if include_attempt:
        attempt = db.get(AgentRunAttempt, item.current_attempt_id) if item.current_attempt_id else None
        result["current_attempt"] = attempt_dict(attempt) if attempt else None
    return result


def headers(
    x_correlation_id: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    return x_correlation_id, idempotency_key


@app.get("/health/live")
def live():
    return {"status": "ok", "service": "runtime-api"}


@app.get("/health/ready")
def ready(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ready", "database": "ok", "pii_enabled": get_settings().pii_enabled}


@app.get("/local-admin/model-config", dependencies=[Depends(require_local_admin)])
def local_model_status():
    return status_payload()


@app.post("/local-admin/model-config", dependencies=[Depends(require_local_admin)])
def local_model_configure(payload: LocalModelConfigRequest):
    return configure_model(payload)


@app.get("/v1/roles")
def list_roles(_: Actor = Depends(current_actor), db: Session = Depends(get_db)):
    return [as_dict(item) for item in db.scalars(select(Role).order_by(Role.id)).all()]


@app.get("/v1/events")
def list_events(_: Actor = Depends(current_actor), db: Session = Depends(get_db)):
    return [as_dict(item) for item in db.scalars(select(OrganizationEvent).order_by(OrganizationEvent.created_at.desc())).all()]


@app.post("/v1/events", status_code=201)
def create_event(payload: EventCreate, actor: Actor = Depends(current_actor), hs=Depends(headers), db: Session = Depends(get_db)):
    ctx = prepare_write(actor, *hs, payload.model_dump())
    if old := find_idempotent(db, ctx):
        return as_dict(db.get(OrganizationEvent, old.resource_id))
    item = OrganizationEvent(event_type=payload.event_type, payload=payload.payload, correlation_id=ctx.correlation_id,
                             created_by=actor.id, content_hash=ctx.request_hash)
    db.add(item); db.flush()
    db.add(Outbox(event_type="organization.event.created", aggregate_type="event", aggregate_id=item.id,
                  payload={"event_id": item.id, "event_type": item.event_type}))
    record_write(db, ctx, "event", item.id, "event.create"); db.commit(); db.refresh(item)
    return as_dict(item)


@app.get("/v1/commitments")
def list_commitments(status: str | None = Query(default=None), _: Actor = Depends(current_actor), db: Session = Depends(get_db)):
    query = select(Commitment).order_by(Commitment.created_at.desc())
    if status:
        query = query.where(Commitment.status == status)
    return [as_dict(item) for item in db.scalars(query).all()]


@app.post("/v1/commitments", status_code=201)
def create_commitment(payload: CommitmentCreate, actor: Actor = Depends(current_actor), hs=Depends(headers), db: Session = Depends(get_db)):
    ctx = prepare_write(actor, *hs, payload.model_dump())
    if old := find_idempotent(db, ctx):
        return as_dict(db.get(Commitment, old.resource_id))
    item = Commitment(**payload.model_dump(), created_by=actor.id, content_hash=ctx.request_hash)
    db.add(item); db.flush()
    db.add(Outbox(event_type="commitment.proposed", aggregate_type="commitment", aggregate_id=item.id, payload={"id": item.id}))
    record_write(db, ctx, "commitment", item.id, "commitment.create"); db.commit(); db.refresh(item)
    return as_dict(item)


TRANSITIONS = {
    "proposed": {"clarifying", "accepted", "rejected", "cancelled"},
    "clarifying": {"proposed", "cancelled"}, "accepted": {"active", "cancelled", "paused"},
    "active": {"waiting", "submitted", "manual_takeover", "paused"},
    "waiting": {"active", "manual_takeover", "paused"}, "submitted": {"fulfilled", "active"},
    "manual_takeover": {"submitted", "paused"}, "paused": {"active", "cancelled"},
}


@app.post("/v1/commitments/{item_id}/transition")
def transition_commitment(item_id: str, payload: CommitmentTransition, actor: Actor = Depends(current_actor), hs=Depends(headers), db: Session = Depends(get_db)):
    item = db.get(Commitment, item_id)
    if not item:
        raise HTTPException(404, "Commitment不存在")
    ctx = prepare_write(actor, *hs, {"id": item_id, **payload.model_dump(), "version": item.version})
    if payload.status not in TRANSITIONS.get(item.status, set()):
        raise HTTPException(409, f"非法状态迁移：{item.status} -> {payload.status}")
    if payload.status == "fulfilled":
        require_any(actor, "company_admin", "product_marketing_owner", "brand_growth_owner")
    item.status = payload.status; item.version += 1; item.content_hash = ctx.request_hash
    record_write(db, ctx, "commitment", item.id, "commitment.transition"); db.commit(); db.refresh(item)
    return as_dict(item)


@app.get("/v1/handoffs")
def list_handoffs(_: Actor = Depends(current_actor), db: Session = Depends(get_db)):
    return [as_dict(x) for x in db.scalars(select(Handoff).order_by(Handoff.created_at.desc())).all()]


@app.post("/v1/handoffs", status_code=201)
def create_handoff(payload: HandoffCreate, actor: Actor = Depends(current_actor), hs=Depends(headers), db: Session = Depends(get_db)):
    ctx = prepare_write(actor, *hs, payload.model_dump())
    if old := find_idempotent(db, ctx): return as_dict(db.get(Handoff, old.resource_id))
    item = Handoff(**payload.model_dump(), content_hash=ctx.request_hash); db.add(item); db.flush()
    record_write(db, ctx, "handoff", item.id, "handoff.create"); db.commit(); db.refresh(item); return as_dict(item)


@app.get("/v1/approvals")
def list_approvals(_: Actor = Depends(current_actor), db: Session = Depends(get_db)):
    return [as_dict(x) for x in db.scalars(select(Approval).order_by(Approval.created_at.desc())).all()]


@app.post("/v1/approvals", status_code=201)
def create_approval(payload: ApprovalCreate, actor: Actor = Depends(current_actor), hs=Depends(headers), db: Session = Depends(get_db)):
    require_any(actor, "company_admin", "product_marketing_owner", "brand_growth_owner")
    ctx = prepare_write(actor, *hs, payload.model_dump())
    if old := find_idempotent(db, ctx): return as_dict(db.get(Approval, old.resource_id))
    item = Approval(**payload.model_dump(), issued_by=actor.id, content_hash=ctx.request_hash); db.add(item); db.flush()
    record_write(db, ctx, "approval", item.id, "approval.issue"); db.commit(); db.refresh(item); return as_dict(item)


@app.get("/v1/runs")
def list_runs(_: Actor = Depends(current_actor), db: Session = Depends(get_db)):
    return [run_dict(db, x) for x in db.scalars(select(AgentRun).order_by(AgentRun.created_at.desc())).all()]


@app.get("/v1/runs/{item_id}")
def get_run(item_id: str, _: Actor = Depends(current_actor), db: Session = Depends(get_db)):
    item = db.get(AgentRun, item_id)
    if not item: raise HTTPException(404, "Run不存在")
    return run_dict(db, item, include_attempt=True)


@app.get("/v1/runs/{item_id}/attempts")
def list_run_attempts(item_id: str, _: Actor = Depends(current_actor), db: Session = Depends(get_db)):
    if not db.get(AgentRun, item_id):
        raise HTTPException(404, "Run不存在")
    items = db.scalars(
        select(AgentRunAttempt).where(AgentRunAttempt.run_id == item_id).order_by(AgentRunAttempt.attempt_no)
    ).all()
    return [attempt_dict(item) for item in items]


@app.get("/v1/runs/{item_id}/timeline")
def get_run_timeline(item_id: str, _: Actor = Depends(current_actor), db: Session = Depends(get_db)):
    if not db.get(AgentRun, item_id):
        raise HTTPException(404, "Run不存在")
    items = db.scalars(
        select(AgentRunTransition)
        .where(AgentRunTransition.run_id == item_id)
        .order_by(AgentRunTransition.sequence_no)
    ).all()
    return [as_dict(item) for item in items]


@app.get("/v1/attempts/{attempt_id}")
def get_attempt(attempt_id: str, _: Actor = Depends(current_actor), db: Session = Depends(get_db)):
    attempt = db.get(AgentRunAttempt, attempt_id)
    if not attempt:
        raise HTTPException(404, "Attempt不存在")
    run = db.get(AgentRun, attempt.run_id)
    return {**attempt_dict(attempt), "run": run_dict(db, run) if run else None}


@app.post("/v1/runs", status_code=202)
def create_run(
    payload: RunCreate,
    actor: Actor = Depends(current_actor),
    hs=Depends(headers),
    traceparent: str | None = Header(default=None),
    tracestate: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    role = db.get(Role, payload.role_id); commitment = db.get(Commitment, payload.commitment_id)
    if not role or not commitment: raise HTTPException(404, "岗位或Commitment不存在")
    if commitment.proposed_role != role.id:
        raise HTTPException(409, "Run岗位必须与Commitment责任岗位一致")
    if commitment.status not in {"accepted", "active"}:
        raise HTTPException(409, "只有accepted/active的Commitment可以启动Run")
    ctx = prepare_write(actor, *hs, payload.model_dump())
    if old := find_idempotent(db, ctx): return run_dict(db, db.get(AgentRun, old.resource_id))
    active_traceparent, active_tracestate = current_trace_headers()
    resolved_execution_mode = payload.execution_mode
    if resolved_execution_mode == "auto":
        resolved_execution_mode = "real" if execution_enabled() else "synthetic"
    if resolved_execution_mode == "real" and not execution_enabled():
        raise HTTPException(409, "真实执行尚未启用，请先在Agent配置中验证DeepSeek")
    item = AgentRun(commitment_id=commitment.id, role_id=role.id, profile_id=role.profile_id,
                    execution_mode=resolved_execution_mode,
                    input_text=payload.input, correlation_id=ctx.correlation_id, created_by=actor.id,
                    content_hash=ctx.request_hash, traceparent=traceparent or active_traceparent,
                    tracestate=tracestate or active_tracestate)
    db.add(item); db.flush()
    append_transition(db, item, "queued", reason="run created", actor=actor.id, allow_same=True)
    db.add(Outbox(event_type="agent.run.requested", aggregate_type="run", aggregate_id=item.id, payload={"run_id": item.id}))
    record_write(db, ctx, "run", item.id, "run.create"); db.commit(); db.refresh(item)
    metrics.add(metrics.run_created, profile_id=item.profile_id)
    log.info("agent run created", extra={
        "run_id": item.id,
        "correlation_id": item.correlation_id,
    })
    return run_dict(db, item)


@app.post("/v1/runs/{item_id}/cancel")
def cancel_run(item_id: str, actor: Actor = Depends(current_actor), hs=Depends(headers), db: Session = Depends(get_db)):
    require_any(actor, "company_admin", "operator", "product_marketing_owner", "brand_growth_owner")
    item_stmt = select(AgentRun).where(AgentRun.id == item_id)
    if db.bind and db.bind.dialect.name == "postgresql":
        item_stmt = item_stmt.with_for_update()
    item = db.scalar(item_stmt)
    if not item:
        raise HTTPException(404, "Run不存在")
    ctx = prepare_write(actor, *hs, {"run_id": item_id, "action": "cancel"})
    if old := find_idempotent(db, ctx):
        return run_dict(db, db.get(AgentRun, old.resource_id), include_attempt=True)
    request_cancellation(db, item, actor.id)
    db.add(Outbox(
        event_type="agent.run.cancellation.requested",
        aggregate_type="run",
        aggregate_id=item.id,
        payload={"run_id": item.id, "attempt_id": item.current_attempt_id},
    ))
    record_write(db, ctx, "run", item.id, "run.cancel.request")
    db.commit(); db.refresh(item)
    return run_dict(db, item, include_attempt=True)


@app.get("/v1/manual-tasks")
def list_manual_tasks(_: Actor = Depends(current_actor), db: Session = Depends(get_db)):
    return [as_dict(x) for x in db.scalars(select(ManualTask).order_by(ManualTask.created_at.desc())).all()]


@app.post("/v1/manual-tasks", status_code=201)
def create_manual_task(payload: ManualTaskCreate, actor: Actor = Depends(current_actor), hs=Depends(headers), db: Session = Depends(get_db)):
    ctx = prepare_write(actor, *hs, payload.model_dump())
    if old := find_idempotent(db, ctx): return as_dict(db.get(ManualTask, old.resource_id))
    item = ManualTask(**payload.model_dump(), content_hash=ctx.request_hash); db.add(item); db.flush()
    record_write(db, ctx, "manual_task", item.id, "manual_task.create"); db.commit(); db.refresh(item); return as_dict(item)


@app.post("/v1/manual-tasks/{item_id}/receipt")
def record_manual_task_receipt(item_id: str, payload: ManualTaskReceipt, actor: Actor = Depends(current_actor),
                               hs=Depends(headers), if_match: str | None = Header(default=None, alias="If-Match"),
                               db: Session = Depends(get_db)):
    require_any(actor, "company_admin", "operator", "brand_growth_owner")
    item = db.get(ManualTask, item_id)
    if not item: raise HTTPException(404, "人工任务不存在")
    if if_match is None or if_match.strip('"') != str(item.version):
        raise HTTPException(412, "If-Match必须等于当前任务版本")
    if payload.status == "simulated":
        expected_case_id = (item.object_ref or {}).get("case_id")
        if expected_case_id != payload.receipt.get("case_id"):
            raise HTTPException(409, "simulated回执必须匹配人工任务所属case_id")
    ctx = prepare_write(actor, *hs, {"id": item_id, "version": item.version, **payload.model_dump()})
    item.status = payload.status; item.receipt = payload.receipt; item.version += 1; item.content_hash = ctx.request_hash
    record_write(db, ctx, "manual_task", item.id, "manual_task.receipt.record")
    db.commit(); db.refresh(item); return as_dict(item)


@app.get("/v1/leads")
def list_lead_stubs(_: Actor = Depends(current_actor), db: Session = Depends(get_db)):
    return [as_dict(x) for x in db.scalars(select(LeadStub).order_by(LeadStub.created_at.desc())).all()]


@app.post("/v1/leads", status_code=201)
def create_lead_stub(payload: LeadStubCreate, actor: Actor = Depends(current_actor), hs=Depends(headers), db: Session = Depends(get_db)):
    require_any(actor, "company_admin", "operator", "brand_growth_owner", "service")
    ctx = prepare_write(actor, *hs, payload.model_dump())
    if old := find_idempotent(db, ctx): return as_dict(db.get(LeadStub, old.resource_id))
    item = LeadStub(**payload.model_dump(), created_by=actor.id, content_hash=ctx.request_hash)
    db.add(item); db.flush()
    record_write(db, ctx, "lead_stub", item.id, "lead_stub.create")
    db.commit(); db.refresh(item); return as_dict(item)


@app.get("/v1/sales-feedback")
def list_sales_feedback(_: Actor = Depends(current_actor), db: Session = Depends(get_db)):
    return [as_dict(x) for x in db.scalars(select(SalesFeedback).order_by(SalesFeedback.created_at.desc())).all()]


@app.post("/v1/sales-feedback", status_code=201)
def create_sales_feedback(payload: SalesFeedbackCreate, actor: Actor = Depends(current_actor), hs=Depends(headers), db: Session = Depends(get_db)):
    require_any(actor, "sales_owner")
    lead = db.get(LeadStub, payload.lead_stub_id)
    if not lead: raise HTTPException(404, "LeadStub不存在")
    if lead.version != payload.lead_version: raise HTTPException(409, "LeadStub版本已漂移")
    ctx = prepare_write(actor, *hs, payload.model_dump())
    if old := find_idempotent(db, ctx): return as_dict(db.get(SalesFeedback, old.resource_id))
    item = SalesFeedback(**payload.model_dump(), sales_actor_id=actor.id,
                         correlation_id=ctx.correlation_id, content_hash=ctx.request_hash)
    db.add(item); db.flush()
    record_write(db, ctx, "sales_feedback", item.id, "sales_feedback.record")
    db.commit(); db.refresh(item); return as_dict(item)


@app.get("/v1/knowledge")
def list_knowledge(_: Actor = Depends(current_actor), db: Session = Depends(get_db)):
    return [as_dict(x) for x in db.scalars(select(KnowledgeItem).order_by(KnowledgeItem.created_at.desc())).all()]


@app.post("/v1/knowledge", status_code=201)
def create_knowledge(payload: KnowledgeCreate, actor: Actor = Depends(current_actor), hs=Depends(headers), db: Session = Depends(get_db)):
    ctx = prepare_write(actor, *hs, payload.model_dump())
    if old := find_idempotent(db, ctx): return as_dict(db.get(KnowledgeItem, old.resource_id))
    data = payload.model_dump(); data["metadata_json"] = data.pop("metadata")
    item = KnowledgeItem(**data, created_by=actor.id, content_hash=ctx.request_hash); db.add(item); db.flush()
    record_write(db, ctx, "knowledge", item.id, "knowledge.create"); db.commit(); db.refresh(item); return as_dict(item)


@app.get("/v1/memory")
def list_memory(profile_id: str | None = None, _: Actor = Depends(current_actor), db: Session = Depends(get_db)):
    query = select(MemoryEntry).where(MemoryEntry.active.is_(True))
    if profile_id: query = query.where(MemoryEntry.profile_id == profile_id)
    return [as_dict(x) for x in db.scalars(query.order_by(MemoryEntry.created_at.desc())).all()]


@app.post("/v1/memory", status_code=201)
def create_memory(payload: MemoryCreate, actor: Actor = Depends(current_actor), hs=Depends(headers), db: Session = Depends(get_db)):
    ctx = prepare_write(actor, *hs, payload.model_dump())
    if old := find_idempotent(db, ctx): return as_dict(db.get(MemoryEntry, old.resource_id))
    item = MemoryEntry(**payload.model_dump(), content_hash=ctx.request_hash); db.add(item); db.flush()
    record_write(db, ctx, "memory", item.id, "memory.create"); db.commit(); db.refresh(item); return as_dict(item)


@app.get("/v1/marketing-cases")
def list_marketing_cases(
    limit: int = Query(default=20, ge=1, le=100),
    _: Actor = Depends(current_actor),
    db: Session = Depends(get_db),
):
    items = db.scalars(select(MarketingCase).order_by(MarketingCase.created_at.desc()).limit(limit)).all()
    return [{**as_dict(item), "next_actions": case_snapshot(db, item)["next_actions"]} for item in items]


@app.post("/v1/marketing-cases", status_code=201)
def create_marketing_case_route(
    payload: MarketingCaseCreate,
    actor: Actor = Depends(current_actor),
    hs=Depends(headers),
    db: Session = Depends(get_db),
):
    require_any(actor, "company_admin", "operator", "product_marketing_owner", "brand_growth_owner")
    if payload.execution_mode == "real" and not execution_enabled():
        raise HTTPException(409, "真实执行尚未启用，请先在Agent配置中验证DeepSeek")
    ctx = prepare_write(actor, *hs, payload.model_dump())
    if old := find_idempotent(db, ctx):
        old_case = db.get(MarketingCase, old.resource_id)
        if not old_case:
            raise HTTPException(409, "幂等记录指向的Marketing Case不存在")
        return case_snapshot(db, old_case)
    item = create_marketing_case(
        db,
        **payload.model_dump(),
        actor_id=actor.id,
        correlation_id=ctx.correlation_id,
        request_hash=ctx.request_hash,
    )
    record_write(db, ctx, "marketing_case", item.id, "marketing_case.create")
    db.commit(); db.refresh(item)
    metrics.add(
        metrics.case_created,
        execution_mode=item.execution_mode,
        platform=item.target_platform,
    )
    log.info("marketing case created", extra={
        "correlation_id": ctx.correlation_id,
        "case_id": item.id,
        "stage_key": item.current_stage,
        "status": item.status,
        "operation": "marketing_case.create",
    })
    return case_snapshot(db, item)


@app.get("/v1/marketing-cases/{item_id}")
def get_marketing_case(
    item_id: str,
    _: Actor = Depends(current_actor),
    db: Session = Depends(get_db),
):
    item = db.get(MarketingCase, item_id)
    if not item:
        raise HTTPException(404, "Marketing Case不存在")
    return case_snapshot(db, item)


@app.post("/v1/marketing-cases/{item_id}/commands")
def command_marketing_case(
    item_id: str,
    payload: MarketingCaseCommand,
    actor: Actor = Depends(current_actor),
    hs=Depends(headers),
    if_match: str | None = Header(default=None, alias="If-Match"),
    traceparent: str | None = Header(default=None),
    tracestate: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    require_any(actor, "company_admin", "operator", "product_marketing_owner", "brand_growth_owner", "sales_owner")
    item_stmt = select(MarketingCase).where(MarketingCase.id == item_id)
    if db.bind and db.bind.dialect.name == "postgresql":
        item_stmt = item_stmt.with_for_update()
    item = db.scalar(item_stmt)
    if not item:
        raise HTTPException(404, "Marketing Case不存在")
    expected_version = None
    if if_match is not None:
        try:
            expected_version = int(if_match.strip('"'))
        except ValueError as exc:
            raise HTTPException(400, "If-Match必须是Case版本号") from exc
    command_body = {"case_id": item_id, "expected_version": expected_version, **payload.model_dump()}
    ctx = prepare_write(actor, *hs, command_body)
    if old := find_idempotent(db, ctx):
        old_case = db.get(MarketingCase, old.resource_id)
        if not old_case:
            raise HTTPException(409, "幂等记录指向的Marketing Case不存在")
        return case_snapshot(db, old_case)
    if expected_version is None:
        raise HTTPException(428, "Marketing Case命令必须携带If-Match")
    if expected_version != item.version:
        raise HTTPException(412, f"Marketing Case版本已变化：当前为{item.version}")
    if (
        item.execution_mode == "real"
        and payload.action in {"start_mo_plan", "start_pma", "start_bga", "start_mo_retrospective", "retry_safe_step"}
        and not execution_enabled()
    ):
        raise HTTPException(409, "真实执行当前未启用，请先在Agent配置中验证DeepSeek")
    active_traceparent, active_tracestate = current_trace_headers()
    try:
        execute_case_command(
            db,
            item,
            action=payload.action,
            payload=payload.payload,
            actor_id=actor.id,
            traceparent=traceparent or active_traceparent,
            tracestate=tracestate or active_tracestate,
        )
    except MarketingCaseConflict as exc:
        metrics.add(
            metrics.case_command_rejected,
            action=payload.action,
            reason="state_conflict",
        )
        log.warning("marketing case command rejected", extra={
            "correlation_id": ctx.correlation_id,
            "case_id": item.id,
            "stage_key": item.current_stage,
            "status": item.status,
            "operation": payload.action,
            "outcome": "rejected",
        })
        raise HTTPException(409, str(exc)) from exc
    record_write(db, ctx, "marketing_case", item.id, f"marketing_case.{payload.action}")
    db.commit(); db.refresh(item)
    log.info("marketing case command completed", extra={
        "correlation_id": ctx.correlation_id,
        "case_id": item.id,
        "stage_key": item.current_stage,
        "status": item.status,
        "operation": payload.action,
        "outcome": "completed",
    })
    return case_snapshot(db, item)


@app.get("/v1/audit")
def list_audit(limit: int = Query(default=100, ge=1, le=500), actor: Actor = Depends(current_actor), db: Session = Depends(get_db)):
    require_any(actor, "company_admin", "auditor", "operator")
    return [as_dict(x) for x in db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)).all()]


@app.get("/v1/runtime-boundary")
def runtime_boundary(_: Actor = Depends(current_actor)):
    return {
        "release": "R0", "pii": "disabled", "publishing": "manual",
        "platforms": ["douyin", "xiaohongshu", "bilibili", "wechat_official"],
        "dormant": ["wechat_channels/SKL-BG-11"], "a2a": False, "production_ha": False,
        "server_time": datetime.now(timezone.utc),
    }


@app.get("/v1/runtime-model")
def runtime_model(_: Actor = Depends(current_actor)):
    settings = get_settings()
    return {
        "provider": settings.hermes_model_provider,
        "model": settings.hermes_model_id,
        "mode": settings.model_mode,
        "execution_enabled": execution_enabled(),
        "credential_location": "model-gateway-secret-file" if settings.model_mode == "deepseek-api-key" else "project-hermes-session",
    }
