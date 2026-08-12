from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from .config import get_settings
from .db import Base, engine, get_db
from .models import (
    AgentRun, Approval, AuditLog, Commitment, Handoff, KnowledgeItem, LeadStub,
    ManualTask, MemoryEntry, OrganizationEvent, Outbox, Role, SalesFeedback,
)
from .policy import canonical_hash, find_idempotent, prepare_write, record_write
from .schemas import (
    ApprovalCreate, CommitmentCreate, CommitmentTransition, EventCreate, HandoffCreate,
    KnowledgeCreate, LeadStubCreate, ManualTaskCreate, ManualTaskReceipt,
    MemoryCreate, RunCreate, SalesFeedbackCreate,
)
from .security import Actor, current_actor, require_any


ROLE_SEEDS = [
    ("DROLE-01", "产品营销 Agent", "pma", "product_marketing_owner"),
    ("DROLE-02", "品牌与增长 Agent", "bga", "brand_growth_owner"),
    ("DROLE-03", "营销协同 Agent", "mo", "brand_growth_owner"),
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
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


def as_dict(obj):
    return {
        attribute.columns[0].name: getattr(obj, attribute.key)
        for attribute in inspect(obj).mapper.column_attrs
    }


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
    return [as_dict(x) for x in db.scalars(select(AgentRun).order_by(AgentRun.created_at.desc())).all()]


@app.get("/v1/runs/{item_id}")
def get_run(item_id: str, _: Actor = Depends(current_actor), db: Session = Depends(get_db)):
    item = db.get(AgentRun, item_id)
    if not item: raise HTTPException(404, "Run不存在")
    return as_dict(item)


@app.post("/v1/runs", status_code=202)
def create_run(payload: RunCreate, actor: Actor = Depends(current_actor), hs=Depends(headers), db: Session = Depends(get_db)):
    role = db.get(Role, payload.role_id); commitment = db.get(Commitment, payload.commitment_id)
    if not role or not commitment: raise HTTPException(404, "岗位或Commitment不存在")
    if commitment.proposed_role != role.id:
        raise HTTPException(409, "Run岗位必须与Commitment责任岗位一致")
    if commitment.status not in {"accepted", "active"}:
        raise HTTPException(409, "只有accepted/active的Commitment可以启动Run")
    ctx = prepare_write(actor, *hs, payload.model_dump())
    if old := find_idempotent(db, ctx): return as_dict(db.get(AgentRun, old.resource_id))
    item = AgentRun(commitment_id=commitment.id, role_id=role.id, profile_id=role.profile_id,
                    input_text=payload.input, correlation_id=ctx.correlation_id, created_by=actor.id,
                    content_hash=ctx.request_hash)
    db.add(item); db.flush()
    db.add(Outbox(event_type="agent.run.requested", aggregate_type="run", aggregate_id=item.id, payload={"run_id": item.id}))
    record_write(db, ctx, "run", item.id, "run.create"); db.commit(); db.refresh(item); return as_dict(item)


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
