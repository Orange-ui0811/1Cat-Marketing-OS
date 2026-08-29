"""Application services used by the eight-page server-backed workspace."""

from __future__ import annotations

from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from .models import AgentProfileConfig, AgentProfileRevision
from .policy import canonical_hash


AGENTS: dict[str, dict[str, Any]] = {
    "MO": {
        "profile_name": "HRM-01-mo",
        "role_name": "Marketing Orchestrator",
        "tools": ["OrganizationEvent", "WorkCommitment", "RoleHandoff"],
        "skills": ["brief-check", "work-plan", "commitment", "route-escalation", "human-handoff", "growth-review"],
        "other_agents": True,
    },
    "PMA": {
        "profile_name": "HRM-02-pma",
        "role_name": "Product Marketing Agent",
        "tools": ["Fact Registry", "Evidence Request", "Manual Task"],
        "skills": ["fact-version", "user-research", "position-claim", "product-assets", "expression-review", "rd-evidence"],
        "other_agents": False,
    },
    "BGA": {
        "profile_name": "HRM-03-bga",
        "role_name": "Brand & Growth Agent",
        "tools": ["Campaign Object", "Content Draft", "Manual Publish"],
        "skills": ["channel-research", "campaign", "content-adapt", "publish-ready", "lead-stub", "attribution"],
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
            {"key": key, "version": "v1.0", "status": "ready", "source": f"profiles/{agent_key.lower()}/{key}"}
            for key in SIX_PACK
        ],
        "skills": [
            {"id": skill, "version": "v1.0", "enabled": True, "status": "ready"}
            for skill in seed["skills"]
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
    }


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
    return {**as_dict(item), "revisions": [as_dict(revision) for revision in revisions]}
