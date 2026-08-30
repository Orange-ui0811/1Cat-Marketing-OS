"""Application services used by the eight-page server-backed workspace."""

from __future__ import annotations

from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from .models import (
    AgentProfileConfig,
    AgentProfileRevision,
    MarketingCase,
    MarketingCaseActivity,
    MarketingCaseChangeRequest,
)
from .hashing import canonical_hash
from .schemas import AgentProfileConfigDocument


AGENTS: dict[str, dict[str, Any]] = {
    "MO": {
        "profile_name": "HRM-01-mo",
        "role_name": "Marketing Orchestrator",
        "tools": ["OrganizationEvent", "WorkCommitment", "RoleHandoff"],
        "skills": [
            ("brief-check", "SKL-OR-01", "核对Brief目标、来源和人工边界"),
            ("work-plan", "SKL-OR-02", "拆解可验收的岗位协作计划"),
            ("commitment", "SKL-OR-03", "建立岗位承诺与完成标准"),
            ("route-escalation", "SKL-OR-04", "识别阻塞并路由人工处理"),
            ("human-handoff", "SKL-OR-05", "组织带版本的岗位交接"),
            ("growth-review", "SKL-OR-06", "聚合证据并形成复盘建议"),
        ],
        "other_agents": True,
    },
    "PMA": {
        "profile_name": "HRM-02-pma",
        "role_name": "Product Marketing Agent",
        "tools": ["Fact Registry", "Evidence Request", "Manual Task"],
        "skills": [
            ("fact-version", "SKL-PM-01", "维护可追溯的产品事实版本"),
            ("user-research", "SKL-PM-02", "整理用户问题与研究证据"),
            ("position-claim", "SKL-PM-03", "形成有证据边界的定位与Claim"),
            ("product-assets", "SKL-PM-04", "组织产品表达候选资产"),
            ("expression-review", "SKL-PM-05", "检查表达准确性与适用范围"),
            ("rd-evidence", "SKL-PM-06", "提出研发证据补充请求"),
        ],
        "other_agents": False,
    },
    "BGA": {
        "profile_name": "HRM-03-bga",
        "role_name": "Brand & Growth Agent",
        "tools": ["Campaign Object", "Content Draft", "Manual Publish"],
        "skills": [
            ("channel-research", "SKL-BG-01", "研究渠道语境与受众行为"),
            ("campaign", "SKL-BG-02", "形成单平台Campaign候选"),
            ("content-adapt", "SKL-BG-03", "生成并适配内容母稿"),
            ("publish-ready", "SKL-BG-04", "检查人工发布准备条件"),
            ("lead-stub", "SKL-BG-05", "创建无PII的线索占位对象"),
            ("attribution", "SKL-BG-06", "整理反馈与归因边界"),
        ],
        "other_agents": False,
    },
}

SIX_PACK = [
    "role_manifest", "soul", "skill_pack", "memory_policy", "daily_operation", "evaluation",
]


def default_config(agent_key: str) -> dict[str, Any]:
    seed = AGENTS[agent_key]
    return {
        "agent": agent_key,
        "profile_name": seed["profile_name"],
        "role_name": seed["role_name"],
        "model": {
            "provider": "Model Gateway",
            "model": "deepseek-v4-pro",
            "endpoint_alias": "gateway/default",
            "credential_ref": "secret://hermes/model-primary",
            "reasoning_level": "low",
            "max_turns": 1,
            "timeout_seconds": 90,
        },
        "six_pack": [
            {
                "key": key,
                "version": "v1.0",
                "status": "ready",
                "source": f"profiles/{agent_key.lower()}/{key}",
                "summary": f"{seed['role_name']} 的 {key} 受控配置",
            }
            for key in SIX_PACK
        ],
        "skills": [
            {
                "id": skill_id,
                "version": "v1.0",
                "enabled": True,
                "status": "ready",
                "source": skill_source,
                "capability": capability,
                "permissions": ["organization-runtime:role-scoped"],
            }
            for skill_id, skill_source, capability in seed["skills"]
        ],
        "permissions": {
            "network": False,
            "terminal": False,
            "browser": False,
            "other_agents": seed["other_agents"],
            "memory_write": True,
            "tools": seed["tools"],
        },
        "memory_summary": "仅保存岗位偏好、术语和协作习惯；不保存正式事实、审批状态或PII。",
        "prompt_templates": {
            "workflow": {
                "version": "v1.0",
                "body": "按照当前案例阶段完成受控候选产出；引用服务端对象ID与版本，明确证据缺口，并保留人工审批和发布边界。",
            },
            "chat": {
                "version": "v1.0",
                "body": "以当前岗位专业视角回答问题；区分服务端已记录事实、专业建议与仍需人工确认的事项，不修改业务状态。",
            },
        },
    }


def normalize_profile_config(agent_key: str, value: dict[str, Any]) -> dict[str, Any]:
    """Fill fields introduced after v1 without mutating the stored revision."""
    base = default_config(agent_key)
    merged = {**base, **dict(value or {})}
    merged["model"] = {**base["model"], **dict(merged.get("model") or {})}
    merged["permissions"] = {**base["permissions"], **dict(merged.get("permissions") or {})}
    merged["prompt_templates"] = {
        key: {**base["prompt_templates"][key], **dict((merged.get("prompt_templates") or {}).get(key) or {})}
        for key in ("workflow", "chat")
    }
    six_by_key = {item.get("key"): item for item in base["six_pack"]}
    for item in merged.get("six_pack") or []:
        if isinstance(item, dict) and item.get("key") in six_by_key:
            six_by_key[item["key"]] = {**six_by_key[item["key"]], **item}
    merged["six_pack"] = [six_by_key[key] for key in SIX_PACK]
    skill_defaults = {item["id"]: item for item in base["skills"]}
    normalized_skills = []
    for item in merged.get("skills") or []:
        if not isinstance(item, dict):
            continue
        fallback = skill_defaults.get(item.get("id"), {})
        normalized_skills.append({
            "version": "v1.0", "enabled": True, "status": "ready", "source": item.get("id", "custom-skill"),
            "capability": "", "permissions": [], **fallback, **item,
        })
    merged["skills"] = normalized_skills or base["skills"]
    return AgentProfileConfigDocument.model_validate(merged).model_dump()


def published_profile_bundle(db: Session, agent_key: str) -> tuple[int, dict[str, Any], str]:
    key = agent_key.upper()
    item = db.scalar(select(AgentProfileConfig).where(AgentProfileConfig.agent_key == key))
    if not item:
        raise LookupError(f"{key}没有服务端Profile")
    revision = db.scalar(select(AgentProfileRevision).where(
        AgentProfileRevision.agent_key == key,
        AgentProfileRevision.version_no == item.published_version,
    ))
    if not revision:
        if item.status != "published":
            raise LookupError(f"{key}没有可用的已发布Profile版本")
        source = dict(item.config_json)
    else:
        source = dict(revision.config_json)
    config = normalize_profile_config(key, source)
    return item.published_version, config, canonical_hash(config)


def ensure_agent_profiles(db: Session) -> None:
    for agent_key in AGENTS:
        if db.scalar(select(AgentProfileConfig).where(AgentProfileConfig.agent_key == agent_key)):
            continue
        config = default_config(agent_key)
        item = AgentProfileConfig(
            id=f"config-{agent_key.lower()}",
            agent_key=agent_key,
            status="published",
            published_version=1,
            config_json=config,
            updated_by="runtime-bootstrap",
            content_hash=canonical_hash(config),
        )
        revision = AgentProfileRevision(
            agent_key=agent_key,
            version_no=1,
            status="published",
            config_json=config,
            summary="初始服务端岗位配置",
            created_by="runtime-bootstrap",
        )
        db.add_all([item, revision])


def as_dict(obj: Any) -> dict[str, Any]:
    return {
        attribute.columns[0].name: getattr(obj, attribute.key)
        for attribute in inspect(obj).mapper.column_attrs
    }


def profile_snapshot(db: Session, item: AgentProfileConfig) -> dict[str, Any]:
    revisions = list(db.scalars(select(AgentProfileRevision).where(
        AgentProfileRevision.agent_key == item.agent_key,
    ).order_by(AgentProfileRevision.version_no.desc())).all())
    published_version, published_config, published_hash = published_profile_bundle(db, item.agent_key)
    return {
        **as_dict(item),
        "config": normalize_profile_config(item.agent_key, item.config_json),
        "published_config": published_config,
        "published_hash": published_hash,
        "published_version": published_version,
        "revisions": [as_dict(revision) for revision in revisions],
    }


def append_case_activity(
    db: Session,
    case: MarketingCase,
    *,
    event_type: str,
    actor_id: str,
    summary: str,
    stage_key: str | None = None,
    correlation_id: str | None = None,
    detail: dict[str, Any] | None = None,
    resource_refs: list[dict[str, Any]] | None = None,
) -> MarketingCaseActivity:
    activity = MarketingCaseActivity(
        case_id=case.id,
        stage_key=stage_key or case.current_stage,
        event_type=event_type,
        actor_id=actor_id,
        summary=summary[:300],
        detail=detail or {},
        resource_refs=resource_refs or [],
        correlation_id=correlation_id or case.correlation_id,
    )
    db.add(activity)
    return activity


def create_case_change_request(
    db: Session,
    case: MarketingCase,
    *,
    channel: str,
    stage_key: str | None,
    summary: str,
    detail: str,
    target_refs: list[dict[str, Any]],
    proposed_change: dict[str, Any],
    actor_id: str,
) -> MarketingCaseChangeRequest:
    content = {
        "case_id": case.id,
        "channel": channel,
        "stage_key": stage_key or case.current_stage,
        "summary": summary,
        "detail": detail,
        "target_refs": target_refs,
        "proposed_change": proposed_change,
    }
    item = MarketingCaseChangeRequest(
        case_id=case.id,
        stage_key=stage_key or case.current_stage,
        channel=channel,
        status="proposed",
        summary=summary,
        detail=detail,
        target_refs=target_refs,
        proposed_change=proposed_change,
        resolution={},
        requested_by=actor_id,
        result_object_refs=[],
        content_hash=canonical_hash(content),
    )
    db.add(item)
    db.flush()
    return item
