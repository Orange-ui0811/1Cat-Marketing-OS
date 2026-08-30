from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


CommitmentStatus = Literal[
    "proposed", "clarifying", "accepted", "active", "waiting", "submitted",
    "fulfilled", "rejected", "manual_takeover", "paused", "cancelled",
]


class EventCreate(BaseModel):
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class CommitmentCreate(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    proposed_role: Literal["DROLE-01", "DROLE-02", "DROLE-03"]
    objective: str = Field(min_length=4)
    acceptance: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)


class CommitmentTransition(BaseModel):
    status: CommitmentStatus
    reason: str = Field(min_length=2)


class HandoffCreate(BaseModel):
    commitment_id: str
    sender_role: Literal["DROLE-01", "DROLE-02", "DROLE-03"]
    recipient: str
    purpose: str
    payload: dict[str, Any] = Field(default_factory=dict)


class ApprovalCreate(BaseModel):
    subject_type: str
    subject_id: str
    subject_version: int = Field(ge=1)
    action: str
    scope: dict[str, Any] = Field(default_factory=dict)


class RunCreate(BaseModel):
    commitment_id: str
    role_id: Literal["DROLE-01", "DROLE-02", "DROLE-03"]
    input: str = Field(min_length=2)
    context_version: int = Field(default=1, ge=1)
    execution_mode: Literal["auto", "synthetic", "real"] = "auto"


class ManualTaskCreate(BaseModel):
    task_type: Literal["publish", "review", "reconcile", "takeover"]
    platform: Literal["douyin", "xiaohongshu", "bilibili", "wechat_official"]
    object_ref: dict[str, Any]
    instructions: str
    assigned_to: str | None = None


class ManualTaskReceipt(BaseModel):
    status: Literal["completed", "failed", "unknown", "simulated"]
    receipt: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_simulated_boundary(self):
        if self.status == "simulated":
            if self.receipt.get("external_effect") is not False or not self.receipt.get("case_id"):
                raise ValueError("simulated回执必须声明external_effect=false并包含case_id")
        return self


class MarketingCaseCreate(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    objective: str = Field(min_length=4)
    brief_body: str = Field(min_length=4)
    source_refs: list[str] = Field(min_length=1)
    target_platform: Literal["douyin", "xiaohongshu", "bilibili", "wechat_official"]
    execution_mode: Literal["synthetic", "real"] = "synthetic"


MarketingCaseAction = Literal[
    "start_mo_plan", "approve_mo_plan", "start_pma", "approve_product",
    "start_bga", "approve_content", "record_simulated_publish",
    "record_synthetic_feedback", "start_mo_retrospective", "accept_retrospective",
    "return_mo_plan", "return_product", "return_content", "return_retrospective",
    "hold_case", "takeover_case", "resume_case", "resolve_unknown",
    "retry_safe_step", "cancel_case",
]


class MarketingCaseCommand(BaseModel):
    action: MarketingCaseAction
    payload: dict[str, Any] = Field(default_factory=dict)


class MarketingMessageAttachment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=180)
    name: str = Field(min_length=1, max_length=240)
    type: str = Field(default="application/octet-stream", min_length=1, max_length=120)
    size: int = Field(ge=0, le=1_000_000_000)
    last_modified: int | None = Field(default=None, ge=0)


class MarketingCaseMessageCreate(BaseModel):
    channel: Literal["MO", "PMA", "BGA"] = "MO"
    body: str = Field(min_length=1, max_length=8000)
    stage_key: str | None = Field(default=None, max_length=60)
    intent: Literal["message", "change_request", "decision_note"] = "message"
    attachments: list[MarketingMessageAttachment] = Field(default_factory=list, max_length=5)


class MarketingCaseChangeRequestCreate(BaseModel):
    channel: Literal["MO", "PMA", "BGA"] = "MO"
    stage_key: str | None = Field(default=None, max_length=60)
    summary: str = Field(min_length=2, max_length=240)
    detail: str = Field(min_length=2, max_length=8000)
    target_refs: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    proposed_change: dict[str, Any] = Field(default_factory=dict)


class MarketingChatTurnCreate(BaseModel):
    channel: Literal["MO", "PMA", "BGA"]
    mode: Literal["consultation", "task"] = "consultation"
    body: str = Field(min_length=1, max_length=8000)
    stage_key: str | None = Field(default=None, max_length=60)
    attachments: list[MarketingMessageAttachment] = Field(default_factory=list, max_length=5)


class AgentModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=2, max_length=80)
    model: str = Field(min_length=2, max_length=120)
    endpoint_alias: str = Field(min_length=2, max_length=160)
    credential_ref: str = Field(min_length=4, max_length=240)
    reasoning_level: Literal["low", "medium", "high"] = "low"
    max_turns: int = Field(default=1, ge=1, le=20)
    timeout_seconds: int = Field(default=90, ge=10, le=600)


class AgentSixPackResource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: Literal["role_manifest", "soul", "skill_pack", "memory_policy", "daily_operation", "evaluation"]
    version: str = Field(min_length=1, max_length=40)
    status: Literal["ready", "warning", "missing"] = "ready"
    source: str = Field(min_length=2, max_length=300)
    summary: str = Field(default="", max_length=500)


class AgentSkillConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=2, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")
    version: str = Field(min_length=1, max_length=40)
    enabled: bool = True
    status: Literal["ready", "warning", "missing"] = "ready"
    source: str = Field(min_length=2, max_length=300)
    capability: str = Field(default="", max_length=500)
    permissions: list[str] = Field(default_factory=list, max_length=30)


class AgentPermissionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    network: bool = False
    terminal: bool = False
    browser: bool = False
    other_agents: bool = False
    memory_write: bool = True
    tools: list[str] = Field(min_length=1, max_length=50)

    @field_validator("tools")
    @classmethod
    def unique_tools(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("工具权限不能重复")
        return cleaned


class AgentPromptTemplate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = Field(min_length=1, max_length=40)
    body: str = Field(min_length=20, max_length=12000)


class AgentPromptTemplates(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow: AgentPromptTemplate
    chat: AgentPromptTemplate


class AgentProfileConfigDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent: Literal["MO", "PMA", "BGA"]
    profile_name: str = Field(min_length=2, max_length=160)
    role_name: str = Field(min_length=2, max_length=160)
    model: AgentModelConfig
    six_pack: list[AgentSixPackResource] = Field(min_length=6, max_length=6)
    skills: list[AgentSkillConfig] = Field(min_length=1, max_length=40)
    permissions: AgentPermissionConfig
    memory_summary: str = Field(min_length=10, max_length=2000)
    prompt_templates: AgentPromptTemplates

    @model_validator(mode="after")
    def validate_profile_bundle(self):
        expected = {"role_manifest", "soul", "skill_pack", "memory_policy", "daily_operation", "evaluation"}
        keys = [item.key for item in self.six_pack]
        if set(keys) != expected or len(keys) != len(set(keys)):
            raise ValueError("岗位六件套必须各出现一次")
        skill_ids = [item.id for item in self.skills]
        if len(skill_ids) != len(set(skill_ids)):
            raise ValueError("Skill ID不能重复")
        if not any(item.enabled and item.status == "ready" for item in self.skills):
            raise ValueError("至少需要一个ready且enabled的Skill")
        return self


class AgentProfileUpdate(BaseModel):
    config: AgentProfileConfigDocument
    summary: str = Field(default="更新岗位配置草稿", min_length=2, max_length=240)


class AgentProfileCommand(BaseModel):
    action: Literal["validate", "publish", "rollback"]
    version: int | None = Field(default=None, ge=1)
    summary: str = Field(default="配置状态变更", min_length=2, max_length=240)


class LeadStubCreate(BaseModel):
    source_record_ref: str = Field(min_length=4, max_length=300)
    touchpoint: str = Field(min_length=2, max_length=80)
    campaign_ref: str | None = Field(default=None, max_length=160)
    content_ref: str | None = Field(default=None, max_length=160)


class SalesFeedbackCreate(BaseModel):
    lead_stub_id: str
    lead_version: int = Field(ge=1)
    inquiry_status: Literal["pending", "valid", "invalid", "needs_more_info"]
    reason_code: str = Field(min_length=2, max_length=80)
    registry_version: str = Field(min_length=1, max_length=40)


class KnowledgeCreate(BaseModel):
    kind: Literal["brief", "evidence", "fact", "claim", "campaign", "content", "review"]
    title: str
    body: str
    source_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryCreate(BaseModel):
    profile_id: Literal["pma", "bga", "mo"]
    category: Literal["stable_preference", "organization_constraint", "object_reference"]
    fact: str = Field(min_length=2, max_length=1000)
    source_ref: str

    @field_validator("fact")
    @classmethod
    def reject_obvious_pii(cls, value: str) -> str:
        import re

        patterns = [r"1[3-9]\d{9}", r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"]
        if any(re.search(pattern, value) for pattern in patterns):
            raise ValueError("R0禁止把手机号或邮箱写入Memory")
        return value
