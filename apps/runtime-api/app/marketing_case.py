"""Persisted, human-gated orchestration for the bounded three-agent demo."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from .models import (
    AgentRun,
    AgentRunAttempt,
    Approval,
    Commitment,
    Handoff,
    KnowledgeItem,
    LeadStub,
    ManualTask,
    MarketingCase,
    MarketingCaseResource,
    MarketingCaseStep,
    Outbox,
    SalesFeedback,
)
from .observability import metrics


STAGES = (
    "brief",
    "mo_plan",
    "pma",
    "product_review",
    "bga",
    "content_review",
    "simulated_publish",
    "feedback",
    "mo_retrospective",
)
ROLE_BY_STAGE = {
    "mo_plan": ("DROLE-03", "mo"),
    "pma": ("DROLE-01", "pma"),
    "bga": ("DROLE-02", "bga"),
    "mo_retrospective": ("DROLE-03", "mo"),
}
REQUIRED_KINDS = {
    "mo_plan": {"review"},
    "pma": {"fact", "claim"},
    "bga": {"campaign", "content"},
    "mo_retrospective": {"review"},
}
ACTION_LABELS = {
    "start_mo_plan": "启动 MO 规划",
    "approve_mo_plan": "人工确认协作计划",
    "start_pma": "启动 PMA",
    "approve_product": "人工审核 Fact / Claim",
    "start_bga": "启动 BGA",
    "approve_content": "人工审核 Campaign / Content",
    "record_simulated_publish": "记录模拟发布回执",
    "record_synthetic_feedback": "登记合成 Lead 与销售反馈",
    "start_mo_retrospective": "启动 MO 复盘",
    "accept_retrospective": "人工确认复盘并完成案例",
    "retry_safe_step": "安全重试当前 Agent 阶段",
    "cancel_case": "取消案例",
}


class MarketingCaseError(RuntimeError):
    pass


class MarketingCaseConflict(MarketingCaseError):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _duration_seconds(started: datetime, completed: datetime) -> float:
    """SQLite may return naive timestamps even for timezone-aware model columns."""
    if started.tzinfo is None and completed.tzinfo is not None:
        completed = completed.replace(tzinfo=None)
    elif started.tzinfo is not None and completed.tzinfo is None:
        started = started.replace(tzinfo=None)
    return max(0.0, (completed - started).total_seconds())


def _hash(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def _as_dict(obj: Any) -> dict[str, Any]:
    return {
        attribute.columns[0].name: getattr(obj, attribute.key)
        for attribute in inspect(obj).mapper.column_attrs
    }


def _trace_id(traceparent: str | None) -> str | None:
    if not traceparent:
        return None
    parts = traceparent.split("-")
    return parts[1] if len(parts) == 4 and len(parts[1]) == 32 else None


def _step(db: Session, case_id: str, key: str) -> MarketingCaseStep:
    item = db.scalar(select(MarketingCaseStep).where(
        MarketingCaseStep.case_id == case_id,
        MarketingCaseStep.step_key == key,
    ))
    if not item:
        raise MarketingCaseConflict(f"案例缺少阶段：{key}")
    return item


def _touch(case: MarketingCase, reason: str) -> None:
    case.version += 1
    case.updated_at = utcnow()
    case.content_hash = _hash({
        "id": case.id,
        "status": case.status,
        "stage": case.current_stage,
        "version": case.version,
        "reason": reason,
    })


def link_resource(
    db: Session,
    case: MarketingCase,
    step: MarketingCaseStep | None,
    resource_type: str,
    resource: Any,
    relation: str,
) -> MarketingCaseResource:
    existing = db.scalar(select(MarketingCaseResource).where(
        MarketingCaseResource.case_id == case.id,
        MarketingCaseResource.resource_type == resource_type,
        MarketingCaseResource.resource_id == resource.id,
        MarketingCaseResource.relation == relation,
    ))
    if existing:
        return existing
    item = MarketingCaseResource(
        case_id=case.id,
        step_id=step.id if step else None,
        resource_type=resource_type,
        resource_id=resource.id,
        resource_version=getattr(resource, "version", None),
        relation=relation,
    )
    db.add(item)
    db.flush()
    return item


def create_marketing_case(
    db: Session,
    *,
    title: str,
    objective: str,
    brief_body: str,
    source_refs: list[str],
    target_platform: str,
    execution_mode: str,
    actor_id: str,
    correlation_id: str,
    request_hash: str,
) -> MarketingCase:
    case = MarketingCase(
        title=title,
        objective=objective,
        target_platform=target_platform,
        execution_mode=execution_mode,
        status="active",
        current_stage="mo_plan",
        created_by=actor_id,
        correlation_id=correlation_id,
        content_hash=request_hash,
    )
    db.add(case)
    db.flush()
    steps: dict[str, MarketingCaseStep] = {}
    for ordinal, key in enumerate(STAGES, start=1):
        status = "completed" if key == "brief" else "ready" if key == "mo_plan" else "pending"
        item = MarketingCaseStep(
            case_id=case.id,
            step_key=key,
            ordinal=ordinal,
            status=status,
            input={},
            output={},
            failure={},
            started_at=utcnow() if key == "brief" else None,
            completed_at=utcnow() if key == "brief" else None,
        )
        db.add(item)
        db.flush()
        steps[key] = item
    brief_data = {
        "kind": "brief",
        "title": f"{title} · Brief",
        "body": brief_body,
        "source_refs": source_refs,
        "metadata": {
            "candidate": True,
            "case_id": case.id,
            "stage_key": "brief",
            "execution_mode": execution_mode,
            "synthetic_business_data": True,
        },
    }
    brief = KnowledgeItem(
        kind="brief",
        title=brief_data["title"],
        body=brief_body,
        source_refs=source_refs,
        metadata_json=brief_data["metadata"],
        created_by=actor_id,
        content_hash=_hash(brief_data),
    )
    db.add(brief)
    db.flush()
    link_resource(db, case, steps["brief"], "knowledge", brief, "brief")
    db.add(Outbox(
        event_type="marketing.case.created",
        aggregate_type="marketing_case",
        aggregate_id=case.id,
        payload={"case_id": case.id, "brief_id": brief.id},
    ))
    return case


def _resource_object(db: Session, ref: MarketingCaseResource) -> Any | None:
    model = {
        "knowledge": KnowledgeItem,
        "commitment": Commitment,
        "run": AgentRun,
        "handoff": Handoff,
        "approval": Approval,
        "manual_task": ManualTask,
        "lead": LeadStub,
        "sales_feedback": SalesFeedback,
    }.get(ref.resource_type)
    return db.get(model, ref.resource_id) if model else None


def allowed_actions(db: Session, case: MarketingCase) -> list[dict[str, str]]:
    if case.status in {"completed", "cancelled"}:
        return []
    step = _step(db, case.id, case.current_stage)
    action = None
    if step.status == "blocked":
        retryability = str(step.failure.get("retryability", "unsafe"))
        actions = ["cancel_case"]
        if retryability == "safe":
            actions.insert(0, "retry_safe_step")
        return [{"action": item, "label": ACTION_LABELS[item]} for item in actions]
    mapping = {
        ("mo_plan", "ready"): "start_mo_plan",
        ("mo_plan", "awaiting_human"): "approve_mo_plan",
        ("pma", "ready"): "start_pma",
        ("product_review", "ready"): "approve_product",
        ("bga", "ready"): "start_bga",
        ("content_review", "ready"): "approve_content",
        ("simulated_publish", "ready"): "record_simulated_publish",
        ("feedback", "ready"): "record_synthetic_feedback",
        ("mo_retrospective", "ready"): "start_mo_retrospective",
        ("mo_retrospective", "awaiting_human"): "accept_retrospective",
    }
    action = mapping.get((case.current_stage, step.status))
    return [{"action": action, "label": ACTION_LABELS[action]}] if action else []


def case_snapshot(db: Session, case: MarketingCase) -> dict[str, Any]:
    steps = list(db.scalars(select(MarketingCaseStep).where(
        MarketingCaseStep.case_id == case.id,
    ).order_by(MarketingCaseStep.ordinal)).all())
    refs = list(db.scalars(select(MarketingCaseResource).where(
        MarketingCaseResource.case_id == case.id,
    ).order_by(MarketingCaseResource.created_at)).all())
    resources = []
    for ref in refs:
        obj = _resource_object(db, ref)
        payload = _as_dict(obj) if obj else None
        if isinstance(obj, AgentRun) and payload is not None:
            payload["trace_id"] = _trace_id(obj.traceparent)
        resources.append({**_as_dict(ref), "resource": payload})
    return {
        **_as_dict(case),
        "stages": [_as_dict(item) for item in steps],
        "resources": resources,
        "next_actions": allowed_actions(db, case),
        "boundary": {
            "publishing": "simulated",
            "external_effect": False,
            "pii": False,
            "business_outcome_claimed": False,
        },
    }


def _instruction(db: Session, case: MarketingCase, stage_key: str) -> str:
    references = []
    resource_refs = list(db.scalars(select(MarketingCaseResource).where(
        MarketingCaseResource.case_id == case.id,
    ).order_by(MarketingCaseResource.created_at)).all())
    for ref in resource_refs:
        item = _resource_object(db, ref)
        if not item:
            continue
        version = getattr(item, "version", ref.resource_version)
        version_ref = f"@v{version}" if version else ""
        if isinstance(item, KnowledgeItem):
            references.append(f"{item.kind}:{item.id}{version_ref}《{item.title}》")
        elif stage_key == "mo_retrospective":
            detail = ""
            if isinstance(item, ManualTask):
                detail = f"status={item.status},external_effect={item.receipt.get('external_effect')}"
            elif isinstance(item, SalesFeedback):
                detail = f"inquiry_status={item.inquiry_status},lead_version={item.lead_version}"
            elif isinstance(item, LeadStub):
                detail = f"touchpoint={item.touchpoint},status={item.status}"
            elif isinstance(item, Approval):
                detail = f"status={item.status},subject={item.subject_id}@v{item.subject_version}"
            elif isinstance(item, Handoff):
                detail = f"status={item.status},recipient={item.recipient}"
            elif isinstance(item, AgentRun):
                detail = f"status={item.status},stage={item.stage_key}"
            elif isinstance(item, Commitment):
                detail = f"status={item.status},role={item.committed_role or item.proposed_role}"
            references.append(f"{ref.resource_type}:{item.id}{version_ref}[{detail or ref.relation}]")
    refs = "；".join(references[-32:])
    common = (
        f"Marketing Case={case.id}；阶段={stage_key}；目标平台={case.target_platform}。"
        f"服务端已汇总这些权威对象引用：{refs}。不使用PII，不访问或写入真实平台。"
        "先调用candidate_kinds_read确认枚举，再尽早调用object_create_candidate持久化所需候选；"
        "source_refs只填写上面已有的对象ID，不必逐个重复读取所有对象。"
    )
    specific = {
        "mo_plan": "请创建至少一个review候选，给出协作计划、责任顺序、证据缺口和人工门禁。",
        "pma": "请创建至少一个fact和一个claim候选，每个Claim明确证据边界和不能宣称的结论。",
        "bga": "请创建至少一个campaign和一个content候选，只面向指定平台；不得创建发布任务。",
        "mo_retrospective": (
            "请创建至少一个review候选，汇总候选、审批、模拟回执和销售反馈，区分事实、推断与待验证项。"
            "review标题和正文不要包含手机号或邮箱；若工具返回参数错误，只修正一次，不伪造持久化结果。"
        ),
    }[stage_key]
    return common + specific


def _accept_pending_handoff(db: Session, case: MarketingCase, recipient: str) -> None:
    refs = db.scalars(select(MarketingCaseResource).where(
        MarketingCaseResource.case_id == case.id,
        MarketingCaseResource.resource_type == "handoff",
    )).all()
    for ref in refs:
        handoff = db.get(Handoff, ref.resource_id)
        if handoff and handoff.recipient == recipient and handoff.status == "pending":
            handoff.status = "accepted"
            handoff.version += 1
            handoff.content_hash = _hash({"handoff_id": handoff.id, "status": "accepted", "case_id": case.id})
            ref.resource_version = handoff.version


def _start_agent(
    db: Session,
    case: MarketingCase,
    stage_key: str,
    actor_id: str,
    traceparent: str | None,
    tracestate: str | None,
) -> AgentRun:
    step = _step(db, case.id, stage_key)
    if step.status != "ready":
        raise MarketingCaseConflict(f"阶段{stage_key}当前不能启动：{step.status}")
    role_id, profile_id = ROLE_BY_STAGE[stage_key]
    _accept_pending_handoff(db, case, role_id)
    instruction = _instruction(db, case, stage_key)
    commitment_payload = {
        "case_id": case.id,
        "stage_key": stage_key,
        "role_id": role_id,
        "objective": instruction,
    }
    commitment = Commitment(
        title=f"{case.title} · {stage_key}",
        status="accepted",
        proposed_role=role_id,
        committed_role=role_id,
        objective=instruction,
        acceptance={"human_confirmation_required": True, "required_kinds": sorted(REQUIRED_KINDS[stage_key])},
        dependencies=[],
        context={
            "case_id": case.id,
            "stage_key": stage_key,
            "execution_mode": case.execution_mode,
            "target_platform": case.target_platform,
            "pii": False,
        },
        created_by=actor_id,
        content_hash=_hash(commitment_payload),
    )
    db.add(commitment)
    db.flush()
    run_payload = {
        "case_id": case.id,
        "stage_key": stage_key,
        "commitment_id": commitment.id,
        "role_id": role_id,
        "input": instruction,
        "execution_mode": case.execution_mode,
    }
    run = AgentRun(
        commitment_id=commitment.id,
        role_id=role_id,
        profile_id=profile_id,
        execution_mode=case.execution_mode,
        case_id=case.id,
        stage_key=stage_key,
        input_text=instruction,
        correlation_id=f"{case.correlation_id}-{stage_key}",
        created_by=actor_id,
        content_hash=_hash(run_payload),
        traceparent=traceparent,
        tracestate=tracestate,
    )
    db.add(run)
    db.flush()
    from .run_state import append_transition

    append_transition(db, run, "queued", reason="marketing case stage run created", actor=actor_id, allow_same=True)
    db.add(Outbox(
        event_type="agent.run.requested",
        aggregate_type="run",
        aggregate_id=run.id,
        payload={"run_id": run.id, "case_id": case.id, "stage_key": stage_key},
    ))
    step.status = "running"
    step.commitment_id = commitment.id
    step.active_run_id = run.id
    step.input = {"instruction": instruction, "execution_mode": case.execution_mode}
    step.output = {}
    step.failure = {}
    step.started_at = utcnow()
    step.updated_at = utcnow()
    case.status = "running"
    case.current_stage = stage_key
    _touch(case, f"start {stage_key}")
    link_resource(db, case, step, "commitment", commitment, f"{stage_key}_commitment")
    link_resource(db, case, step, "run", run, f"{stage_key}_run")
    return run


def _knowledge_for_step(db: Session, case: MarketingCase, step_key: str) -> list[KnowledgeItem]:
    step = _step(db, case.id, step_key)
    refs = db.scalars(select(MarketingCaseResource).where(
        MarketingCaseResource.case_id == case.id,
        MarketingCaseResource.step_id == step.id,
        MarketingCaseResource.resource_type == "knowledge",
    )).all()
    return [item for ref in refs if (item := db.get(KnowledgeItem, ref.resource_id))]


def _fulfill_commitment(db: Session, step: MarketingCaseStep, reason: str) -> None:
    commitment = db.get(Commitment, step.commitment_id) if step.commitment_id else None
    if commitment and commitment.status == "submitted":
        commitment.status = "fulfilled"
        commitment.version += 1
        commitment.content_hash = _hash({"commitment_id": commitment.id, "status": "fulfilled", "reason": reason})


def _create_approval(
    db: Session,
    case: MarketingCase,
    step: MarketingCaseStep,
    subject: KnowledgeItem,
    action: str,
    actor_id: str,
) -> Approval:
    approval = Approval(
        subject_type="knowledge",
        subject_id=subject.id,
        subject_version=subject.version,
        action=action,
        status="issued",
        scope={"case_id": case.id, "stage_key": step.step_key, "external_publish": False},
        issued_by=actor_id,
        remaining_uses=1,
        content_hash=_hash({"case_id": case.id, "subject": subject.id, "version": subject.version, "action": action}),
    )
    db.add(approval)
    db.flush()
    link_resource(db, case, step, "approval", approval, action)
    return approval


def _create_handoff(
    db: Session,
    case: MarketingCase,
    step: MarketingCaseStep,
    sender: str,
    recipient: str,
    purpose: str,
    artifact_ids: list[str],
) -> Handoff:
    payload = {"case_id": case.id, "artifact_ids": artifact_ids, "external_effect": False}
    handoff = Handoff(
        commitment_id=step.commitment_id or "",
        sender_role=sender,
        recipient=recipient,
        purpose=purpose,
        status="pending",
        payload=payload,
        content_hash=_hash(payload),
    )
    db.add(handoff)
    db.flush()
    link_resource(db, case, step, "handoff", handoff, f"handoff_to_{recipient}")
    return handoff


def _complete_step_and_ready_next(
    db: Session,
    case: MarketingCase,
    current: str,
    next_key: str,
    reason: str,
) -> None:
    step = _step(db, case.id, current)
    step.status = "completed"
    step.completed_at = utcnow()
    if step.started_at:
        metrics.record(
            metrics.case_stage_duration,
            _duration_seconds(step.started_at, step.completed_at),
            stage_key=current,
            execution_mode=case.execution_mode,
        )
    step.updated_at = utcnow()
    next_step = _step(db, case.id, next_key)
    next_step.status = "ready"
    next_step.updated_at = utcnow()
    case.current_stage = next_key
    case.status = "active" if next_key in ROLE_BY_STAGE else "awaiting_human"
    _touch(case, reason)


def execute_case_command(
    db: Session,
    case: MarketingCase,
    *,
    action: str,
    payload: dict[str, Any],
    actor_id: str,
    traceparent: str | None,
    tracestate: str | None,
) -> None:
    if action == "start_mo_plan":
        _start_agent(db, case, "mo_plan", actor_id, traceparent, tracestate)
        return
    if action == "approve_mo_plan":
        step = _step(db, case.id, "mo_plan")
        if case.current_stage != "mo_plan" or step.status != "awaiting_human":
            raise MarketingCaseConflict("MO计划尚未进入人工确认")
        items = _knowledge_for_step(db, case, "mo_plan")
        for item in items:
            _create_approval(db, case, step, item, "route_to_pma", actor_id)
        _fulfill_commitment(db, step, "human approved MO plan")
        _create_handoff(db, case, step, "DROLE-03", "DROLE-01", "按已确认计划交给PMA", [x.id for x in items])
        _complete_step_and_ready_next(db, case, "mo_plan", "pma", "approve MO plan")
        return
    if action == "start_pma":
        _start_agent(db, case, "pma", actor_id, traceparent, tracestate)
        return
    if action == "approve_product":
        step = _step(db, case.id, "product_review")
        if case.current_stage != "product_review" or step.status != "ready":
            raise MarketingCaseConflict("产品候选尚未进入人工审核")
        items = _knowledge_for_step(db, case, "pma")
        kinds = {x.kind for x in items}
        if not {"fact", "claim"}.issubset(kinds):
            raise MarketingCaseConflict("产品审核至少需要fact和claim")
        for item in items:
            _create_approval(db, case, step, item, "handoff_to_bga", actor_id)
        _fulfill_commitment(db, _step(db, case.id, "pma"), "human approved product candidates")
        _create_handoff(db, case, step, "DROLE-01", "DROLE-02", "把已审核产品表达交给BGA", [x.id for x in items])
        _complete_step_and_ready_next(db, case, "product_review", "bga", "approve product candidates")
        return
    if action == "start_bga":
        _start_agent(db, case, "bga", actor_id, traceparent, tracestate)
        return
    if action == "approve_content":
        step = _step(db, case.id, "content_review")
        if case.current_stage != "content_review" or step.status != "ready":
            raise MarketingCaseConflict("内容候选尚未进入人工审核")
        items = _knowledge_for_step(db, case, "bga")
        kinds = {x.kind for x in items}
        if not {"campaign", "content"}.issubset(kinds):
            raise MarketingCaseConflict("内容审核至少需要campaign和content")
        approvals = [_create_approval(db, case, step, item, "prepare_manual_publish", actor_id) for item in items]
        _fulfill_commitment(db, _step(db, case.id, "bga"), "human approved campaign and content")
        object_ref = {
            "case_id": case.id,
            "objects": [{"id": x.id, "version": x.version, "kind": x.kind} for x in items],
            "approval_ids": [x.id for x in approvals],
        }
        task = ManualTask(
            task_type="publish",
            platform=case.target_platform,
            status="pending",
            object_ref=object_ref,
            instructions="仅执行演示模拟回执；不得登录或写入真实内容平台。",
            receipt={},
            assigned_to=actor_id,
            content_hash=_hash(object_ref),
        )
        db.add(task)
        db.flush()
        link_resource(db, case, step, "manual_task", task, "simulated_publish_task")
        _complete_step_and_ready_next(db, case, "content_review", "simulated_publish", "approve content")
        return
    if action == "record_simulated_publish":
        step = _step(db, case.id, "simulated_publish")
        if case.current_stage != "simulated_publish" or step.status != "ready":
            raise MarketingCaseConflict("模拟发布阶段尚未就绪")
        task_ref = db.scalar(select(MarketingCaseResource).where(
            MarketingCaseResource.case_id == case.id,
            MarketingCaseResource.resource_type == "manual_task",
            MarketingCaseResource.relation == "simulated_publish_task",
        ))
        task = db.get(ManualTask, task_ref.resource_id) if task_ref else None
        if not task or task.status != "pending":
            raise MarketingCaseConflict("没有可填写的人工发布任务")
        task.status = "simulated"
        task.receipt = {
            "external_effect": False,
            "case_id": case.id,
            "note": str(payload.get("note") or "演示流程，未登录或写入真实平台"),
        }
        task.version += 1
        task.content_hash = _hash(task.receipt)
        task_ref.resource_version = task.version
        _complete_step_and_ready_next(db, case, "simulated_publish", "feedback", "record simulated receipt")
        return
    if action == "record_synthetic_feedback":
        step = _step(db, case.id, "feedback")
        if case.current_stage != "feedback" or step.status != "ready":
            raise MarketingCaseConflict("反馈阶段尚未就绪")
        campaign = next((x for x in _knowledge_for_step(db, case, "bga") if x.kind == "campaign"), None)
        content = next((x for x in _knowledge_for_step(db, case, "bga") if x.kind == "content"), None)
        touchpoint = str(payload.get("touchpoint") or case.target_platform)
        inquiry_status = str(payload.get("inquiry_status") or "valid")
        reason_code = str(payload.get("reason_code") or "synthetic_demo_signal")
        if not 2 <= len(touchpoint) <= 80:
            raise MarketingCaseConflict("touchpoint长度必须在2到80之间")
        if inquiry_status not in {"pending", "valid", "invalid", "needs_more_info"}:
            raise MarketingCaseConflict("销售反馈状态不在允许枚举中")
        if not 2 <= len(reason_code) <= 80:
            raise MarketingCaseConflict("reason_code长度必须在2到80之间")
        lead = LeadStub(
            source_record_ref=f"synthetic://marketing-case/{case.id}/touchpoint-001",
            touchpoint=touchpoint,
            campaign_ref=campaign.id if campaign else None,
            content_ref=content.id if content else None,
            status="registered",
            created_by=actor_id,
            content_hash=_hash({"case_id": case.id, "synthetic": True}),
        )
        db.add(lead)
        db.flush()
        feedback = SalesFeedback(
            lead_stub_id=lead.id,
            lead_version=lead.version,
            inquiry_status=inquiry_status,
            reason_code=reason_code,
            registry_version="demo-v1",
            sales_actor_id=actor_id,
            correlation_id=case.correlation_id,
            content_hash=_hash({"lead_id": lead.id, "case_id": case.id, "synthetic": True}),
        )
        db.add(feedback)
        db.flush()
        link_resource(db, case, step, "lead", lead, "synthetic_lead")
        link_resource(db, case, step, "sales_feedback", feedback, "synthetic_sales_feedback")
        _complete_step_and_ready_next(db, case, "feedback", "mo_retrospective", "record synthetic feedback")
        return
    if action == "start_mo_retrospective":
        _start_agent(db, case, "mo_retrospective", actor_id, traceparent, tracestate)
        return
    if action == "accept_retrospective":
        step = _step(db, case.id, "mo_retrospective")
        if case.current_stage != "mo_retrospective" or step.status != "awaiting_human":
            raise MarketingCaseConflict("MO复盘尚未进入人工确认")
        items = _knowledge_for_step(db, case, "mo_retrospective")
        for item in items:
            _create_approval(db, case, step, item, "accept_retrospective", actor_id)
        _fulfill_commitment(db, step, "human accepted retrospective")
        step.status = "completed"
        step.completed_at = utcnow()
        if step.started_at:
            metrics.record(
                metrics.case_stage_duration,
                _duration_seconds(step.started_at, step.completed_at),
                stage_key=step.step_key,
                execution_mode=case.execution_mode,
            )
        case.status = "completed"
        metrics.add(
            metrics.case_completed,
            execution_mode=case.execution_mode,
            platform=case.target_platform,
        )
        _touch(case, "accept retrospective")
        db.add(Outbox(
            event_type="marketing.case.completed",
            aggregate_type="marketing_case",
            aggregate_id=case.id,
            payload={"case_id": case.id, "external_effect": False},
        ))
        return
    if action == "retry_safe_step":
        step = _step(db, case.id, case.current_stage)
        if step.status != "blocked" or step.failure.get("retryability") != "safe" or not step.commitment_id:
            raise MarketingCaseConflict("当前阶段不允许安全重试")
        old_run = db.get(AgentRun, step.active_run_id) if step.active_run_id else None
        if not old_run:
            raise MarketingCaseConflict("没有可重试的Run")
        run = AgentRun(
            commitment_id=old_run.commitment_id,
            role_id=old_run.role_id,
            profile_id=old_run.profile_id,
            execution_mode=case.execution_mode,
            case_id=case.id,
            stage_key=step.step_key,
            input_text=old_run.input_text,
            correlation_id=f"{case.correlation_id}-{step.step_key}-retry",
            created_by=actor_id,
            content_hash=_hash({"retry_of": old_run.id, "case_id": case.id}),
            traceparent=traceparent,
            tracestate=tracestate,
        )
        db.add(run)
        db.flush()
        from .run_state import append_transition

        append_transition(db, run, "queued", reason="human approved safe workflow retry", actor=actor_id, allow_same=True)
        step.active_run_id = run.id
        step.status = "running"
        step.failure = {}
        case.status = "running"
        _touch(case, "retry safe step")
        link_resource(db, case, step, "run", run, f"{step.step_key}_retry_run")
        return
    if action == "cancel_case":
        step = _step(db, case.id, case.current_stage)
        run = db.get(AgentRun, step.active_run_id) if step.active_run_id else None
        if run and run.status not in {"evidence_accepted", "failed", "cancelled", "unknown"}:
            from .run_state import request_cancellation

            request_cancellation(db, run, actor_id)
            if run.status == "cancelled":
                return
            step.status = "blocked"
            step.failure = {"failure_class": "case_cancellation_requested", "retryability": "unsafe"}
            case.status = "blocked"
            _touch(case, "request case cancellation")
            return
        case.status = "cancelled"
        _touch(case, "cancel case after terminal or before work")
        return
    raise MarketingCaseConflict(f"不支持的案例命令：{action}")


def prepare_synthetic_candidates(db: Session, run: AgentRun, attempt: AgentRunAttempt) -> list[KnowledgeItem]:
    if run.execution_mode != "synthetic":
        return []
    step = db.scalar(select(MarketingCaseStep).where(MarketingCaseStep.active_run_id == run.id))
    if not step or step.step_key not in REQUIRED_KINDS:
        return []
    case = db.get(MarketingCase, step.case_id)
    if not case:
        return []
    existing = [item for item in db.scalars(select(KnowledgeItem)).all()
                if item.metadata_json.get("attempt_id") == attempt.id]
    if existing:
        return existing
    templates = {
        "mo_plan": [("review", "MO协作计划候选", "先由PMA整理事实与Claim，经人类审核后交给BGA；所有发布保持模拟人工边界。")],
        "pma": [
            ("fact", "合成产品事实候选", "基于Brief的合成事实，仅用于演示，不外推为真实产品结论。"),
            ("claim", "有证据边界的Claim候选", "该表达仅在合成Brief条件下成立，需要人类审核和真实证据补充。"),
        ],
        "bga": [
            ("campaign", f"{case.target_platform} Campaign候选", "围绕已审核Claim形成的单平台合成Campaign，不代表真实投放。"),
            ("content", f"{case.target_platform} 内容候选", "供人工审核的内容母稿；系统不会登录、发布或触达真实用户。"),
        ],
        "mo_retrospective": [("review", "MO增长复盘候选", "汇总技术链路、模拟回执与合成反馈；不把运行成功当作营销效果。")],
    }
    source_refs = [f"synthetic://marketing-case/{case.id}/{step.step_key}"]
    created = []
    for kind, title, body in templates[step.step_key]:
        metadata = {
            "candidate": True,
            "case_id": case.id,
            "stage_key": step.step_key,
            "role_id": run.role_id,
            "commitment_id": run.commitment_id,
            "attempt_id": attempt.id,
            "execution_mode": "synthetic",
        }
        item = KnowledgeItem(
            kind=kind,
            title=title,
            body=body,
            source_refs=source_refs,
            metadata_json=metadata,
            created_by="runtime-worker-synthetic",
            content_hash=_hash({"kind": kind, "title": title, "body": body, "metadata": metadata}),
        )
        db.add(item)
        db.flush()
        link_resource(db, case, step, "knowledge", item, f"{step.step_key}_{kind}")
        created.append(item)
    return created


def sync_case_after_run_terminal(db: Session, run: AgentRun) -> None:
    step = db.scalar(select(MarketingCaseStep).where(MarketingCaseStep.active_run_id == run.id))
    if not step or step.status not in {"running", "blocked"}:
        return
    case = db.get(MarketingCase, step.case_id)
    if not case or case.status == "cancelled":
        return
    if run.status == "evidence_accepted":
        candidates = [item for item in db.scalars(select(KnowledgeItem)).all()
                      if item.metadata_json.get("attempt_id") == run.current_attempt_id]
        for item in candidates:
            link_resource(db, case, step, "knowledge", item, f"{step.step_key}_{item.kind}")
        kinds = {item.kind for item in candidates}
        missing = sorted(REQUIRED_KINDS.get(step.step_key, set()) - kinds)
        if missing:
            step.status = "blocked"
            step.failure = {
                "failure_class": "missing_required_artifacts",
                "retryability": "safe",
                "missing_kinds": missing,
            }
            case.status = "blocked"
            metrics.add(
                metrics.case_blocked,
                failure_class="missing_required_artifacts",
                stage_key=step.step_key,
                execution_mode=case.execution_mode,
            )
            _touch(case, "missing required artifacts")
            return
        step.output = {"candidate_ids": [item.id for item in candidates], "candidate_kinds": sorted(kinds)}
        step.failure = {}
        if step.step_key in {"mo_plan", "mo_retrospective"}:
            step.status = "awaiting_human"
            case.status = "awaiting_human"
            _touch(case, f"{step.step_key} awaits human")
        elif step.step_key == "pma":
            _complete_step_and_ready_next(db, case, "pma", "product_review", "PMA candidates ready")
        elif step.step_key == "bga":
            _complete_step_and_ready_next(db, case, "bga", "content_review", "BGA candidates ready")
        return
    if run.status in {"failed", "cancelled", "unknown"}:
        attempt = db.get(AgentRunAttempt, run.current_attempt_id) if run.current_attempt_id else None
        retryability = attempt.retryability if attempt else "unsafe"
        step.status = "blocked"
        step.failure = {
            "failure_class": attempt.failure_class if attempt else f"run_{run.status}",
            "retryability": retryability,
            "run_status": run.status,
        }
        case.status = "blocked"
        metrics.add(
            metrics.case_blocked,
            failure_class=step.failure["failure_class"],
            stage_key=step.step_key,
            execution_mode=case.execution_mode,
        )
        _touch(case, f"run terminal {run.status}")
