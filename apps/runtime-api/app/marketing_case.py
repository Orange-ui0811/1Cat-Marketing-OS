"""Persisted, human-gated orchestration for the bounded three-agent demo."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from .models import (
    AgentProfileConfig,
    AgentRun,
    AgentRunAttempt,
    Approval,
    Commitment,
    Handoff,
    KnowledgeItem,
    LeadStub,
    ManualTask,
    MarketingCase,
    MarketingCaseMessage,
    MarketingDecision,
    MarketingDeliverable,
    MarketingDeliverableRevision,
    MarketingReconciliation,
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
MINIMUM_BODY_LENGTH = {
    "mo_plan": {"review": 180},
    "pma": {"fact": 120, "claim": 160},
    "bga": {"campaign": 260, "content": 900},
    "mo_retrospective": {"review": 260},
}
DELIVERABLE_SECTION_KEYS = (
    "executive_summary",
    "audience_and_problem",
    "verified_facts",
    "claims_and_boundaries",
    "campaign_strategy",
    "content_package",
    "publishing_and_feedback",
    "measurement_and_risk",
    "retrospective",
    "evidence_index",
)
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
    "accept_retrospective": "人工确认最终方案并完成案例",
    "return_mo_plan": "退回 MO 计划修改",
    "return_product": "退回 PMA 候选修改",
    "return_content": "退回 BGA 内容修改",
    "return_retrospective": "退回最终方案修改",
    "hold_case": "HOLD 当前案例",
    "takeover_case": "转为人工接管",
    "resume_case": "恢复人工暂停案例",
    "resolve_unknown": "提交 Unknown 人工对账",
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
        existing.resource_version = getattr(resource, "version", existing.resource_version)
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
    db.add(MarketingCaseMessage(
        case_id=case.id,
        stage_key="brief",
        channel="MO",
        sender_type="system",
        intent="message",
        body="Brief 已持久化。MO 可在任务中心启动规划；所有后续对象、审核和交接都绑定本案例。",
        attachments=[],
        created_by="runtime-system",
    ))
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
        "deliverable": MarketingDeliverable,
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
        if step.failure.get("failure_class") in {"human_hold", "human_takeover"}:
            actions.insert(0, "resume_case")
        if step.failure.get("run_status") == "unknown":
            actions.insert(0, "resolve_unknown")
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
    if not action:
        return []
    actions = [action]
    return_mapping = {
        "approve_mo_plan": "return_mo_plan",
        "approve_product": "return_product",
        "approve_content": "return_content",
        "accept_retrospective": "return_retrospective",
    }
    if action in return_mapping:
        actions.append(return_mapping[action])
    if case.status != "running":
        actions.extend(["hold_case", "takeover_case"])
    actions.append("cancel_case")
    return [{"action": item, "label": ACTION_LABELS[item]} for item in actions]


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
    deliverable = db.scalar(select(MarketingDeliverable).where(MarketingDeliverable.case_id == case.id))
    deliverable_history = list(db.scalars(select(MarketingDeliverableRevision).where(
        MarketingDeliverableRevision.case_id == case.id,
    ).order_by(MarketingDeliverableRevision.version_no.desc())).all())
    messages = list(db.scalars(select(MarketingCaseMessage).where(
        MarketingCaseMessage.case_id == case.id,
    ).order_by(MarketingCaseMessage.created_at)).all())
    decisions = list(db.scalars(select(MarketingDecision).where(
        MarketingDecision.case_id == case.id,
    ).order_by(MarketingDecision.created_at)).all())
    reconciliations = list(db.scalars(select(MarketingReconciliation).where(
        MarketingReconciliation.case_id == case.id,
    ).order_by(MarketingReconciliation.created_at)).all())
    return {
        **_as_dict(case),
        "stages": [_as_dict(item) for item in steps],
        "resources": resources,
        "final_deliverable": _as_dict(deliverable) if deliverable else None,
        "deliverable_history": [_as_dict(item) for item in deliverable_history],
        "messages": [_as_dict(item) for item in messages],
        "decisions": [_as_dict(item) for item in decisions],
        "reconciliations": [_as_dict(item) for item in reconciliations],
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
        f"案例标题={case.title}；业务目标={case.objective}。"
        f"服务端已汇总这些权威对象引用：{refs}。不使用PII，不访问或写入真实平台。"
        "先调用candidate_kinds_read确认枚举，再尽早调用object_create_candidate持久化所需候选；"
        "source_refs只填写上面已有的对象ID，不必逐个重复读取所有对象。"
        "正文必须是可直接审阅的业务材料，不要只写流程说明、占位句或‘后续补充’。"
    )
    specific = {
        "mo_plan": (
            "请创建至少一个review候选，正文不少于180字，明确受众假设、PMA/BGA/MO责任顺序、"
            "输入输出、证据缺口、人工门禁和完成标准。"
        ),
        "pma": (
            "请创建至少一个fact和一个claim候选。fact正文不少于120字，逐项区分Brief事实、"
            "可验证事实和待验证假设；claim正文不少于160字，给出允许表达、禁止表达、所需证据和适用边界。"
        ),
        "bga": (
            "请创建至少一个campaign和一个content候选，只面向指定平台；campaign正文不少于260字，"
            "包含受众、核心信息、内容支柱、CTA、节奏和指标；content正文不少于900字，提供可直接审核的"
            "完整脚本/母稿、标题、开场、分段正文、CTA与风险提示。不得创建发布任务。"
        ),
        "mo_retrospective": (
            "请创建至少一个review候选，正文不少于260字，汇总候选、审批、模拟回执和销售反馈，"
            "区分已证实事实、推断、待验证项、风险和下一轮动作。"
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
    profile_config = db.scalar(select(AgentProfileConfig).where(
        AgentProfileConfig.agent_key == profile_id.upper(),
    ))
    profile_version = profile_config.published_version if profile_config else None
    profile_snapshot = dict(profile_config.config_json) if profile_config else {}
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
            "profile_version": profile_version,
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
        profile_version=profile_version,
        profile_snapshot=profile_snapshot,
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


def _quality_failures(stage_key: str, candidates: list[KnowledgeItem]) -> dict[str, dict[str, int]]:
    failures: dict[str, dict[str, int]] = {}
    for kind, minimum in MINIMUM_BODY_LENGTH.get(stage_key, {}).items():
        lengths = [len(item.body.strip()) for item in candidates if item.kind == kind]
        maximum = max(lengths, default=0)
        if maximum < minimum:
            failures[kind] = {"minimum": minimum, "actual": maximum}
    return failures


def _knowledge_for_case(db: Session, case: MarketingCase) -> list[KnowledgeItem]:
    refs = db.scalars(select(MarketingCaseResource).where(
        MarketingCaseResource.case_id == case.id,
        MarketingCaseResource.resource_type == "knowledge",
    ).order_by(MarketingCaseResource.created_at)).all()
    result: list[KnowledgeItem] = []
    seen: set[str] = set()
    for ref in refs:
        item = db.get(KnowledgeItem, ref.resource_id)
        if item and item.id not in seen:
            result.append(item)
            seen.add(item.id)
    return result


def _section(key: str, title: str, content: str, sources: list[KnowledgeItem]) -> dict[str, Any]:
    return {
        "key": key,
        "title": title,
        "content": content.strip(),
        "source_refs": [
            {"type": "knowledge", "id": item.id, "version": item.version, "kind": item.kind}
            for item in sources
        ],
    }


def _format_knowledge(items: list[KnowledgeItem], empty: str) -> str:
    if not items:
        return empty
    return "\n\n".join(f"### {item.title}\n{item.body.strip()}" for item in items)


def _render_markdown(title: str, case: MarketingCase, sections: list[dict[str, Any]]) -> str:
    header = (
        f"# {title}\n\n"
        f"> Case `{case.id}` · 平台 `{case.target_platform}` · 执行模式 `{case.execution_mode}`\n\n"
        "> 本方案由服务端持久化对象汇编，并经人工门禁确认。发布仅为 simulated，"
        "external_effect=false；不代表真实营销效果。\n"
    )
    body = []
    for index, section in enumerate(sections, start=1):
        body.append(f"## {index}. {section['title']}\n\n{section['content']}")
    return header + "\n\n" + "\n\n".join(body) + "\n"


def _deliverable_validation(document: dict[str, Any], markdown: str) -> list[str]:
    errors: list[str] = []
    sections = document.get("sections") if isinstance(document, dict) else None
    if not isinstance(sections, list):
        return ["sections_missing"]
    by_key = {str(item.get("key")): item for item in sections if isinstance(item, dict)}
    for key in DELIVERABLE_SECTION_KEYS:
        section = by_key.get(key)
        if not section:
            errors.append(f"missing_section:{key}")
            continue
        minimum = 500 if key == "content_package" else 80
        if len(str(section.get("content") or "").strip()) < minimum:
            errors.append(f"section_too_short:{key}")
    if len(markdown.strip()) < 2200:
        errors.append("markdown_too_short")
    evidence = document.get("evidence_index")
    if not isinstance(evidence, list) or len(evidence) < 7:
        errors.append("evidence_index_incomplete")
    return errors


def _build_final_deliverable(
    db: Session,
    case: MarketingCase,
    *,
    actor_id: str,
) -> tuple[MarketingDeliverable, list[str]]:
    items = [item for item in _knowledge_for_case(db, case) if item.status != "returned"]
    by_kind: dict[str, list[KnowledgeItem]] = {}
    for item in items:
        by_kind.setdefault(item.kind, []).append(item)
    brief = by_kind.get("brief", [])
    mo_reviews = [
        item for item in by_kind.get("review", [])
        if item.metadata_json.get("stage_key") == "mo_plan"
    ]
    retrospectives = [
        item for item in by_kind.get("review", [])
        if item.metadata_json.get("stage_key") == "mo_retrospective"
    ]
    facts = by_kind.get("fact", [])
    claims = by_kind.get("claim", [])
    campaigns = by_kind.get("campaign", [])
    contents = by_kind.get("content", [])

    refs = list(db.scalars(select(MarketingCaseResource).where(
        MarketingCaseResource.case_id == case.id,
    ).order_by(MarketingCaseResource.created_at)).all())
    manual_tasks = [db.get(ManualTask, ref.resource_id) for ref in refs if ref.resource_type == "manual_task"]
    leads = [db.get(LeadStub, ref.resource_id) for ref in refs if ref.resource_type == "lead"]
    feedback = [db.get(SalesFeedback, ref.resource_id) for ref in refs if ref.resource_type == "sales_feedback"]
    manual_tasks = [item for item in manual_tasks if item]
    leads = [item for item in leads if item]
    feedback = [item for item in feedback if item]

    publish_lines = [
        f"- 发布任务 `{item.id}@v{item.version}`：状态 `{item.status}`；"
        f"external_effect={item.receipt.get('external_effect', False)}；备注：{item.receipt.get('note', '无')}"
        for item in manual_tasks
    ] or ["- 尚无发布回执；不得将流程状态解释为真实发布。"]
    feedback_lines = [
        f"- 合成 Lead `{item.id}@v{item.version}`：触点 `{item.touchpoint}`，状态 `{item.status}`。"
        for item in leads
    ] + [
        f"- 销售反馈 `{item.id}`：状态 `{item.inquiry_status}`，原因码 `{item.reason_code}`，"
        f"绑定 Lead 版本 `{item.lead_version}`。"
        for item in feedback
    ]
    evidence_index = []
    for ref in refs:
        obj = _resource_object(db, ref)
        if not obj:
            continue
        evidence_index.append({
            "type": ref.resource_type,
            "id": ref.resource_id,
            "version": getattr(obj, "version", ref.resource_version),
            "relation": ref.relation,
        })
    evidence_lines = [
        f"- `{item['type']}:{item['id']}@v{item['version'] or '-'}` — {item['relation']}"
        for item in evidence_index
    ]

    sections = [
        _section(
            "executive_summary",
            "执行摘要",
            (
                f"本案例《{case.title}》面向 {case.target_platform}，目标是：{case.objective}。"
                "MO 负责规划与复盘，PMA 负责事实和表达边界，BGA 负责活动策略与完整内容母稿；"
                "每次岗位交接均由人工审核控制。最终交付是一份可继续编辑、可追溯到版本化对象的方案，"
                "不是自动发布结果，也不声称已经获得真实营销效果。\n\n"
                + _format_knowledge(mo_reviews, "MO 未提供额外规划正文。")
            ),
            mo_reviews,
        ),
        _section(
            "audience_and_problem",
            "受众、问题与 Brief",
            (
                "目标受众以 Brief 明确的人群为准；在没有真实调研和用户数据时，受众描述仅作为待验证假设。"
                "内容要优先回答受众为什么需要理解该主题、常见误区是什么，以及完成阅读/观看后能采取什么行动。\n\n"
                + _format_knowledge(brief, f"业务目标：{case.objective}")
            ),
            brief,
        ),
        _section(
            "verified_facts",
            "PMA 事实底稿",
            _format_knowledge(facts, "未形成可用事实；方案不得进入最终确认。"),
            facts,
        ),
        _section(
            "claims_and_boundaries",
            "Claim、允许表达与禁止表达",
            (
                _format_knowledge(claims, "未形成可用 Claim；方案不得进入最终确认。")
                + "\n\n统一边界：只能把服务端 Run、Attempt、审批、模拟回执表述为项目演示证据；"
                "不得外推为生产规模、真实客户采用、真实发布、转化率提升或商业收益。任何新增数字都必须补充来源和版本。"
            ),
            claims,
        ),
        _section(
            "campaign_strategy",
            "Campaign 策略",
            _format_knowledge(campaigns, "未形成可执行 Campaign；方案不得进入最终确认。"),
            campaigns,
        ),
        _section(
            "content_package",
            "完整内容母稿",
            _format_knowledge(contents, "未形成完整内容母稿；方案不得进入最终确认。"),
            contents,
        ),
        _section(
            "publishing_and_feedback",
            "发布、回执与反馈",
            (
                "发布动作由人类控制。本案例只记录模拟回执，不登录、不调用、不写入任何真实内容平台。\n\n"
                + "\n".join(publish_lines + feedback_lines)
            ),
            [],
        ),
        _section(
            "measurement_and_risk",
            "度量、风险与人工门禁",
            (
                "建议在真实执行前由人类确定基线和观察窗口：内容完成率、有效互动率、CTA 点击率、"
                "有效询盘率与负面反馈率。当前合成 Lead 只能验证数据链路，不能作为效果基线。\n\n"
                "必须保留四个门禁：MO 计划确认、PMA 事实/Claim 审核、BGA 内容审核、最终方案确认。"
                "主要风险包括证据不足、模型生成越界、重复执行、外部结果未知和把 simulated 回执误报为真实发布；"
                "对应措施是版本审批、Attempt/Lease 防旧写回、unknown 人工对账和 external_effect=false 声明。"
            ),
            [],
        ),
        _section(
            "retrospective",
            "MO 复盘与下一轮动作",
            _format_knowledge(retrospectives, "未形成可用复盘；方案不得进入最终确认。"),
            retrospectives,
        ),
        _section(
            "evidence_index",
            "证据与版本索引",
            "\n".join(evidence_lines) or "- 无可追溯证据。",
            [],
        ),
    ]
    title = f"{case.title} · 完整营销执行方案"
    markdown = _render_markdown(title, case, sections)
    document = {
        "format_version": "marketing-plan/v1",
        "case": {
            "id": case.id,
            "title": case.title,
            "objective": case.objective,
            "target_platform": case.target_platform,
            "execution_mode": case.execution_mode,
        },
        "sections": sections,
        "evidence_index": evidence_index,
        "boundary": {
            "publishing": "simulated",
            "external_effect": False,
            "pii": False,
            "business_outcome_claimed": False,
        },
    }
    source_refs = [
        {"type": "knowledge", "id": item.id, "version": item.version, "kind": item.kind}
        for item in items
    ]
    content_hash = _hash({"document": document, "markdown": markdown, "sources": source_refs})
    deliverable = db.scalar(select(MarketingDeliverable).where(MarketingDeliverable.case_id == case.id))
    if deliverable:
        deliverable.title = title
        deliverable.status = "draft"
        deliverable.format_version = "marketing-plan/v1"
        deliverable.document_json = document
        deliverable.markdown = markdown
        deliverable.source_refs = source_refs
        deliverable.accepted_by = None
        deliverable.accepted_at = None
        deliverable.version += 1
        deliverable.content_hash = content_hash
        deliverable.updated_at = utcnow()
    else:
        deliverable = MarketingDeliverable(
            case_id=case.id,
            title=title,
            status="draft",
            format_version="marketing-plan/v1",
            document_json=document,
            markdown=markdown,
            source_refs=source_refs,
            created_by=actor_id,
            content_hash=content_hash,
        )
        db.add(deliverable)
        db.flush()
    retrospective_step = _step(db, case.id, "mo_retrospective")
    link_resource(db, case, retrospective_step, "deliverable", deliverable, "final_marketing_plan")
    _record_deliverable_revision(db, deliverable, actor_id)
    return deliverable, _deliverable_validation(document, markdown)


def _fulfill_commitment(db: Session, step: MarketingCaseStep, reason: str) -> None:
    commitment = db.get(Commitment, step.commitment_id) if step.commitment_id else None
    if commitment and commitment.status == "submitted":
        commitment.status = "fulfilled"
        commitment.version += 1
        commitment.content_hash = _hash({"commitment_id": commitment.id, "status": "fulfilled", "reason": reason})


def _record_deliverable_revision(
    db: Session,
    deliverable: MarketingDeliverable,
    actor_id: str,
) -> MarketingDeliverableRevision:
    db.flush()
    existing = db.scalar(select(MarketingDeliverableRevision).where(
        MarketingDeliverableRevision.deliverable_id == deliverable.id,
        MarketingDeliverableRevision.version_no == deliverable.version,
    ))
    if existing:
        return existing
    revision = MarketingDeliverableRevision(
        deliverable_id=deliverable.id,
        case_id=deliverable.case_id,
        version_no=deliverable.version,
        status=deliverable.status,
        document_json=deliverable.document_json,
        markdown=deliverable.markdown,
        source_refs=deliverable.source_refs,
        content_hash=deliverable.content_hash,
        created_by=actor_id,
    )
    db.add(revision)
    db.flush()
    return revision


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


def _accept_deliverable(
    db: Session,
    case: MarketingCase,
    step: MarketingCaseStep,
    deliverable: MarketingDeliverable,
    actor_id: str,
) -> Approval:
    errors = _deliverable_validation(deliverable.document_json, deliverable.markdown)
    if errors:
        raise MarketingCaseConflict(f"最终方案不完整：{','.join(errors)}")
    if deliverable.status != "draft":
        raise MarketingCaseConflict(f"最终方案当前不能确认：{deliverable.status}")
    approval = Approval(
        subject_type="marketing_deliverable",
        subject_id=deliverable.id,
        subject_version=deliverable.version,
        action="accept_final_deliverable",
        status="issued",
        scope={"case_id": case.id, "stage_key": step.step_key, "external_publish": False},
        issued_by=actor_id,
        remaining_uses=1,
        content_hash=_hash({
            "case_id": case.id,
            "subject": deliverable.id,
            "version": deliverable.version,
            "action": "accept_final_deliverable",
        }),
    )
    db.add(approval)
    db.flush()
    link_resource(db, case, step, "approval", approval, "accept_final_deliverable")
    deliverable.status = "accepted"
    deliverable.accepted_by = actor_id
    deliverable.accepted_at = utcnow()
    deliverable.version += 1
    deliverable.updated_at = utcnow()
    deliverable.content_hash = _hash({
        "id": deliverable.id,
        "status": deliverable.status,
        "accepted_by": actor_id,
        "accepted_at": deliverable.accepted_at,
        "previous_hash": deliverable.content_hash,
    })
    deliverable_ref = db.scalar(select(MarketingCaseResource).where(
        MarketingCaseResource.case_id == case.id,
        MarketingCaseResource.resource_type == "deliverable",
        MarketingCaseResource.resource_id == deliverable.id,
    ))
    if deliverable_ref:
        deliverable_ref.resource_version = deliverable.version
    _record_deliverable_revision(db, deliverable, actor_id)
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


def _subject_refs(db: Session, case: MarketingCase, stage_key: str) -> list[dict[str, Any]]:
    producer = {
        "product_review": "pma",
        "content_review": "bga",
    }.get(stage_key, stage_key)
    items = _knowledge_for_step(db, case, producer) if producer in {"mo_plan", "pma", "bga", "mo_retrospective"} else []
    refs = [
        {"type": "knowledge", "id": item.id, "version": item.version, "kind": item.kind}
        for item in items
    ]
    if stage_key == "mo_retrospective":
        deliverable = db.scalar(select(MarketingDeliverable).where(MarketingDeliverable.case_id == case.id))
        if deliverable:
            refs.append({"type": "marketing_deliverable", "id": deliverable.id, "version": deliverable.version})
    return refs


def _record_decision(
    db: Session,
    case: MarketingCase,
    step: MarketingCaseStep,
    *,
    decision: str,
    reason: str,
    actor_id: str,
    metadata: dict[str, Any] | None = None,
) -> MarketingDecision:
    item = MarketingDecision(
        case_id=case.id,
        stage_key=step.step_key,
        decision=decision,
        reason=reason,
        subject_refs=_subject_refs(db, case, step.step_key),
        metadata_json=metadata or {},
        actor_id=actor_id,
    )
    db.add(item)
    db.flush()
    return item


def _return_for_revision(
    db: Session,
    case: MarketingCase,
    *,
    current_stage: str,
    producer_stage: str,
    reason: str,
    actor_id: str,
) -> None:
    current = _step(db, case.id, current_stage)
    expected_status = "awaiting_human" if current_stage in {"mo_plan", "mo_retrospective"} else "ready"
    if case.current_stage != current_stage or current.status != expected_status:
        raise MarketingCaseConflict(f"阶段{current_stage}当前不能退回")
    _record_decision(db, case, current, decision="returned", reason=reason, actor_id=actor_id)
    producer = _step(db, case.id, producer_stage)
    old_commitment = db.get(Commitment, producer.commitment_id) if producer.commitment_id else None
    if old_commitment and old_commitment.status not in {"fulfilled", "cancelled"}:
        old_commitment.status = "cancelled"
        old_commitment.version += 1
        old_commitment.content_hash = _hash({"id": old_commitment.id, "status": "cancelled", "reason": reason})
    for item in _knowledge_for_step(db, case, producer_stage):
        if item.status == "candidate":
            item.status = "returned"
            item.version += 1
            item.content_hash = _hash({"id": item.id, "status": "returned", "reason": reason})
    if current_stage != producer_stage:
        current.status = "pending"
        current.failure = {}
        current.updated_at = utcnow()
    producer.status = "ready"
    producer.active_run_id = None
    producer.completed_at = None
    producer.failure = {}
    producer.updated_at = utcnow()
    case.current_stage = producer_stage
    case.status = "active"
    _touch(case, f"return {current_stage} to {producer_stage}")


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
        items = [item for item in _knowledge_for_step(db, case, "mo_plan") if item.status != "returned"]
        _record_decision(
            db, case, step, decision="approved",
            reason=str(payload.get("reason") or "人工确认 MO 协作计划"), actor_id=actor_id,
        )
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
        items = [item for item in _knowledge_for_step(db, case, "pma") if item.status != "returned"]
        kinds = {x.kind for x in items}
        if not {"fact", "claim"}.issubset(kinds):
            raise MarketingCaseConflict("产品审核至少需要fact和claim")
        _record_decision(
            db, case, step, decision="approved",
            reason=str(payload.get("reason") or "人工确认 Fact / Claim 及其表达边界"), actor_id=actor_id,
        )
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
        items = [item for item in _knowledge_for_step(db, case, "bga") if item.status != "returned"]
        kinds = {x.kind for x in items}
        if not {"campaign", "content"}.issubset(kinds):
            raise MarketingCaseConflict("内容审核至少需要campaign和content")
        _record_decision(
            db, case, step, decision="approved",
            reason=str(payload.get("reason") or "人工确认 Campaign / Content 并允许建立模拟发布任务"), actor_id=actor_id,
        )
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
        items = [item for item in _knowledge_for_step(db, case, "mo_retrospective") if item.status != "returned"]
        for item in items:
            _create_approval(db, case, step, item, "accept_retrospective", actor_id)
        deliverable = db.scalar(select(MarketingDeliverable).where(
            MarketingDeliverable.case_id == case.id,
        ))
        if not deliverable:
            raise MarketingCaseConflict("最终方案尚未生成，不能完成案例")
        _record_decision(
            db, case, step, decision="approved",
            reason=str(payload.get("reason") or "人工确认 MO 复盘与最终营销方案"), actor_id=actor_id,
        )
        _accept_deliverable(db, case, step, deliverable, actor_id)
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
            payload={
                "case_id": case.id,
                "deliverable_id": deliverable.id,
                "external_effect": False,
            },
        ))
        return
    if action == "return_mo_plan":
        _return_for_revision(
            db, case, current_stage="mo_plan", producer_stage="mo_plan",
            reason=str(payload.get("reason") or "计划需要补充后重新提交"), actor_id=actor_id,
        )
        return
    if action == "return_product":
        _return_for_revision(
            db, case, current_stage="product_review", producer_stage="pma",
            reason=str(payload.get("reason") or "Fact / Claim 需要修改后重新提交"), actor_id=actor_id,
        )
        return
    if action == "return_content":
        _return_for_revision(
            db, case, current_stage="content_review", producer_stage="bga",
            reason=str(payload.get("reason") or "Campaign / Content 需要修改后重新提交"), actor_id=actor_id,
        )
        return
    if action == "return_retrospective":
        _return_for_revision(
            db, case, current_stage="mo_retrospective", producer_stage="mo_retrospective",
            reason=str(payload.get("reason") or "最终方案需要修改后重新提交"), actor_id=actor_id,
        )
        return
    if action in {"hold_case", "takeover_case"}:
        if case.status == "running":
            raise MarketingCaseConflict("Agent 正在执行；请先取消 Run，确认终态后再暂停或接管")
        step = _step(db, case.id, case.current_stage)
        reason = str(payload.get("reason") or ("人工暂停当前案例" if action == "hold_case" else "人工接管当前案例"))
        previous_status = step.status
        _record_decision(
            db, case, step,
            decision="hold" if action == "hold_case" else "takeover",
            reason=reason, actor_id=actor_id,
        )
        step.status = "blocked"
        step.failure = {
            "failure_class": "human_hold" if action == "hold_case" else "human_takeover",
            "retryability": "manual",
            "previous_step_status": previous_status,
            "reason": reason,
        }
        case.status = "blocked"
        _touch(case, action)
        return
    if action == "resume_case":
        step = _step(db, case.id, case.current_stage)
        if step.status != "blocked" or step.failure.get("failure_class") not in {"human_hold", "human_takeover"}:
            raise MarketingCaseConflict("当前案例不是可恢复的人工暂停状态")
        reason = str(payload.get("reason") or "人工确认恢复案例")
        _record_decision(db, case, step, decision="resumed", reason=reason, actor_id=actor_id)
        previous = str(step.failure.get("previous_step_status") or "ready")
        step.status = previous if previous in {"ready", "awaiting_human"} else "ready"
        step.failure = {}
        case.status = "awaiting_human" if step.status == "awaiting_human" else "active"
        _touch(case, "resume human hold")
        return
    if action == "resolve_unknown":
        step = _step(db, case.id, case.current_stage)
        run = db.get(AgentRun, step.active_run_id) if step.active_run_id else None
        if step.status != "blocked" or not run or run.status != "unknown":
            raise MarketingCaseConflict("当前阶段没有需要人工对账的 Unknown Run")
        resolution = str(payload.get("resolution") or "")
        if resolution not in {"confirmed_succeeded", "confirmed_failed", "confirmed_cancelled", "abandoned"}:
            raise MarketingCaseConflict("Unknown 对账结论不在允许范围内")
        note = str(payload.get("note") or "").strip()
        if len(note) < 2:
            raise MarketingCaseConflict("Unknown 对账必须填写依据")
        attempt = db.get(AgentRunAttempt, run.current_attempt_id) if run.current_attempt_id else None
        reconciliation = MarketingReconciliation(
            case_id=case.id,
            step_id=step.id,
            run_id=run.id,
            attempt_id=attempt.id if attempt else None,
            resolution=resolution,
            note=note,
            evidence=dict(payload.get("evidence") or {}),
            actor_id=actor_id,
        )
        db.add(reconciliation)
        db.flush()
        _record_decision(
            db, case, step, decision="reconciled", reason=note, actor_id=actor_id,
            metadata={"resolution": resolution, "run_id": run.id},
        )
        if resolution in {"confirmed_failed", "confirmed_cancelled"}:
            step.failure = {
                **step.failure,
                "failure_class": f"human_{resolution}",
                "retryability": "safe",
                "run_status": resolution,
                "reconciliation_id": reconciliation.id,
            }
            _touch(case, f"reconcile unknown as {resolution}")
            return
        if resolution == "abandoned":
            case.status = "cancelled"
            _touch(case, "abandon unknown case")
            return
        candidates = _knowledge_for_step(db, case, step.step_key)
        kinds = {item.kind for item in candidates if item.status != "returned"}
        missing = sorted(REQUIRED_KINDS.get(step.step_key, set()) - kinds)
        if missing:
            raise MarketingCaseConflict(f"确认成功前仍缺少对象：{','.join(missing)}")
        step.failure = {}
        step.output = {"candidate_ids": [item.id for item in candidates], "candidate_kinds": sorted(kinds), "human_reconciled": True}
        if step.step_key == "mo_plan":
            step.status = "awaiting_human"; case.status = "awaiting_human"
        elif step.step_key == "pma":
            _complete_step_and_ready_next(db, case, "pma", "product_review", "human reconciled PMA success")
        elif step.step_key == "bga":
            _complete_step_and_ready_next(db, case, "bga", "content_review", "human reconciled BGA success")
        elif step.step_key == "mo_retrospective":
            deliverable, errors = _build_final_deliverable(db, case, actor_id="runtime-deliverable-assembler")
            if errors:
                raise MarketingCaseConflict(f"最终方案仍不完整：{','.join(errors)}")
            step.output["deliverable_id"] = deliverable.id
            step.status = "awaiting_human"; case.status = "awaiting_human"
        _touch(case, "human reconciled unknown as succeeded")
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
    brief_items = _knowledge_for_step(db, case, "brief")
    brief_text = brief_items[0].body.strip() if brief_items else case.objective
    templates = {
        "mo_plan": [(
            "review",
            "MO协作计划与人工门禁",
            f"案例目标是“{case.objective}”，目标平台为 {case.target_platform}。第一阶段由PMA依据Brief“{brief_text}”"
            "整理可追溯事实，明确哪些内容来自输入、哪些只是待验证假设，并为每条Claim写出允许和禁止表达。"
            "产品负责人完成人工审核后，MO通过持久化Handoff把已批准对象及版本交给BGA。BGA只生成单平台Campaign和"
            "完整内容母稿，不创建发布动作；内容负责人审核通过后，Runtime才建立人工发布任务，而且演示中只能记录"
            "simulated回执。随后系统创建不含PII的合成Lead与销售反馈，MO依据全部对象、审批、Run、Attempt和回执完成复盘。"
            "完成标准是四次Agent Run进入evidence_accepted、所有必需候选达到正文质量门槛、两次交接可追踪、人工门禁齐全，"
            "最终方案能够按对象ID和版本反查。证据缺口包括真实用户洞察、真实平台表现和商业转化，因此不得声称已经发布或产生收益。"
        )],
        "pma": [
            (
                "fact",
                "PMA事实底稿与待验证项",
                f"已知的服务端事实：案例标题为“{case.title}”，业务目标为“{case.objective}”，目标平台是"
                f" {case.target_platform}，Brief正文为“{brief_text}”。系统将MO、PMA、BGA的Run、Attempt、候选对象、审批和"
                "Handoff持久化，并在人工批准后才允许进入下一阶段；发布任务只接受external_effect=false的模拟回执。"
                "这些事实只能证明本次工程链路和方案生成过程。真实受众规模、平台流量、转化率、客户采用和商业收益均没有真实数据，"
                "必须列为待验证项，不能从合成Lead或模型输出中推导。"
            ),
            (
                "claim",
                "可用Claim、证据边界与禁用表达",
                "允许表达：‘该项目演示了一条由MO规划、PMA整理事实、BGA生成内容并由人类逐级审核的Agent Runtime链路’；"
                "‘Run状态、Attempt历史、人工审批、模拟回执和最终方案都能通过服务端对象ID与版本追踪’；"
                "‘Worker使用租约、心跳和旧Token写回保护来支持可恢复执行’。适用边界仅限当前演示环境和已有测试证据。"
                "禁止表达：‘已经在生产大规模运行’、‘已自动发布到真实平台’、‘带来了真实线索或转化增长’、"
                "‘模型输出天然可信’。如果要使用性能、稳定性或营销效果数字，必须补充可复现测试方法、样本、观察窗口、"
                "来源链接和对象版本，并再次经过产品与内容人工审批。"
            ),
        ],
        "bga": [
            (
                "campaign",
                f"{case.target_platform} 单平台Campaign方案",
                f"Campaign主题：{case.title}。核心受众是正在学习Agent工程、只会调用模型API但尚未理解Runtime边界的"
                f"开发者与系统平台实习候选人。核心信息不是‘模型有多聪明’，而是‘Agent需要一套可恢复、可审核、可追踪的执行系统’。"
                f"内容只投向 {case.target_platform}：第一支主内容用一次任务从Brief到最终方案的九阶段路径建立认知；第二组拆解"
                "Run/Attempt/Lease/Heartbeat；第三组解释人工门禁和unknown边界。主CTA是查看架构研修台、在本机运行合成Demo并"
                "沿Case ID检查状态、对象和Trace。节奏建议为一支5分钟主内容加三张知识卡片，不做跨平台自动分发。"
                "审核前指标仅作为定义：完整观看率、知识卡保存率、Demo启动成功率和有效技术问题数；没有真实发布时全部保持N/A。"
                "风险控制包括不展示密钥、不使用PII、不承诺生产规模、不把simulated回执当作发布成功，并保留标题与正文的人工终审。"
            ),
            (
                "content",
                f"{case.target_platform} 5分钟完整内容脚本",
                f"标题：为什么一个Agent项目不能只有Prompt？我用《{case.title}》跑通了一条可恢复执行链。\n\n"
                "【开场 0:00—0:30】\n如果你把模型API接上一个Prompt，再加几个工具调用，这当然可以叫Agent原型；"
                "但只要Worker中途退出、同一个任务被重复领取，或者外部工具已经执行却没有返回结果，你就会发现：真正难的不是"
                "让模型回答一次，而是让系统知道任务现在处于什么状态、谁有权继续、哪些结果能被相信。今天不展示一个聊天机器人，"
                "而是用一个媒体任务，拆开一条Agent Runtime的完整工程链路。\n\n"
                f"【第一部分 0:30—1:15：任务从哪里开始】\n本次业务目标是“{case.objective}”。Brief明确写着：{brief_text}。"
                "系统创建的不是浏览器里的一份临时表单，而是持久化Marketing Case。它包含九个固定阶段：Brief、MO规划、PMA、"
                "产品审核、BGA、内容审核、模拟发布、反馈和MO复盘。刷新页面后，状态仍由服务端恢复。这样做的价值是把业务流程和"
                "Agent执行分开：页面只展示服务端允许的下一步，不能靠前端按钮跳过人工门禁。\n\n"
                "【第二部分 1:15—2:05：三个Agent不是并排的头像】\nMO先规划责任和顺序，明确证据缺口；人类确认后，系统创建"
                "版本化Handoff交给PMA。PMA只负责事实与Claim：哪些可以说，哪些不能说，还缺什么证据。产品负责人审核对象ID和"
                "版本后，BGA才接收交接并生成Campaign和这份完整母稿。BGA没有发布权限；内容通过人工审核后，Runtime才创建"
                "Manual Task。这种关系比三个Agent在界面上互相连线更重要，因为每次交接都有服务端事实、版本和责任边界。\n\n"
                "【第三部分 2:05—3:05：Runtime如何面对失败】\n每个AgentRun都有不可覆盖的Attempt历史。Worker领取任务时，在同一"
                "数据库事务里创建Attempt并取得Lease；运行过程中发送Heartbeat，所有结果写回必须匹配current_attempt_id和"
                "lease_token。旧Worker即使后来恢复，也不能覆盖新Attempt。如果模型还没有被真正调用，租约过期后可以安全重试；"
                "如果外部Run已经启动但终态无法确认，系统进入unknown，禁止自动重试，等待人类对账。这不是‘失败处理不够智能’，"
                "恰恰是为了避免把一次可能有副作用的操作执行两遍。\n\n"
                "【第四部分 3:05—3:50：成功不等于业务完成】\nRun进入evidence_accepted只代表执行证据被系统接受，不代表Campaign"
                "已经发布，更不代表产生了转化。PMA必须有Fact和Claim，BGA必须有Campaign和完整Content，MO复盘必须区分事实、"
                "推断与待验证项。正文过短或对象缺失时，Case会进入blocked，并且只有标记为safe的情况才能由人发起重试。即使通过"
                "内容审核，本次发布也只记录simulated回执，明确external_effect=false。\n\n"
                "【第五部分 3:50—4:35：怎么定位一次执行】\n从工作台可以沿Case ID看到Commitment、Handoff、Approval、Knowledge、"
                "Run与Attempt；沿correlation ID查看结构化日志，沿trace ID打开Jaeger，再在Grafana检查队列、延迟、租约过期和"
                "unknown指标。跨越人工等待的阶段不会伪造成一条连续Trace，而是用Case ID和Span Link关联。这使排查问题时能够回答："
                "是谁在什么版本上做了什么、失败发生在哪次Attempt、系统为什么允许或拒绝下一步。\n\n"
                "【结尾 4:35—5:00】\n所以，一个能回答问题的Agent原型和一个可演示的Agent Runtime，差别在状态、恢复、权限、人工边界"
                "与可观测性。下一步可以自己运行合成模式，创建一个Case，故意杀掉Worker，再检查新旧Attempt和最终方案是否仍然可追踪。"
                "如果你也在做Agent基础设施，先别急着堆更多工具：先让一条最小链路在失败之后还能说清楚发生了什么。\n\n"
                "风险提示：本内容只陈述当前演示项目的工程能力；未连接真实内容平台，未使用真实用户数据，也未声明任何营销收益。"
            ),
        ],
        "mo_retrospective": [(
            "review",
            "MO最终复盘与下一轮验证计划",
            "本轮已经形成MO规划、PMA事实与Claim、BGA Campaign与完整内容母稿，并经过对应人工门禁；内容审核后才创建发布任务，"
            "回执明确为simulated且external_effect=false。系统还登记了不含PII的合成Lead和销售反馈，用来验证对象绑定与版本链路，"
            "不能把它解释为真实用户兴趣或转化。已证实的事实是四个Agent阶段均形成持久化候选，Run和Attempt可追踪，交接与审批"
            "能够限制推进顺序。合理推断是这套结构具备继续接入真实评测和平台适配器的基础，但尚未验证生产负载、真实平台API变化、"
            "真实内容质量和营销效果。下一轮优先动作：用一组人工标注样例评测Fact/Claim准确性；执行Worker中断与unknown对账演练；"
            "为内容质量建立明确评分表；在保持人工发布的前提下采集真实但脱敏的观看与反馈数据。所有新增结论都要记录来源、版本、"
            "观察窗口和审批人，避免用技术链路完成替代业务结果。"
        )],
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
        quality_failures = _quality_failures(step.step_key, candidates)
        if quality_failures:
            step.status = "blocked"
            step.failure = {
                "failure_class": "incomplete_required_artifacts",
                "retryability": "safe",
                "quality_failures": quality_failures,
            }
            case.status = "blocked"
            metrics.add(
                metrics.case_blocked,
                failure_class="incomplete_required_artifacts",
                stage_key=step.step_key,
                execution_mode=case.execution_mode,
            )
            _touch(case, "required artifacts below quality threshold")
            return
        step.output = {"candidate_ids": [item.id for item in candidates], "candidate_kinds": sorted(kinds)}
        step.failure = {}
        if step.step_key == "mo_retrospective":
            deliverable, deliverable_errors = _build_final_deliverable(
                db,
                case,
                actor_id="runtime-deliverable-assembler",
            )
            if deliverable_errors:
                step.status = "blocked"
                step.failure = {
                    "failure_class": "incomplete_final_deliverable",
                    "retryability": "safe",
                    "validation_errors": deliverable_errors,
                    "deliverable_id": deliverable.id,
                }
                case.status = "blocked"
                metrics.add(
                    metrics.case_blocked,
                    failure_class="incomplete_final_deliverable",
                    stage_key=step.step_key,
                    execution_mode=case.execution_mode,
                )
                _touch(case, "final deliverable validation failed")
                return
            step.output["deliverable_id"] = deliverable.id
            step.output["deliverable_version"] = deliverable.version
            step.status = "awaiting_human"
            case.status = "awaiting_human"
            _touch(case, "final deliverable awaits human")
        elif step.step_key == "mo_plan":
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
