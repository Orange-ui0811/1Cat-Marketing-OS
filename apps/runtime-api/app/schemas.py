from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


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


class ManualTaskCreate(BaseModel):
    task_type: Literal["publish", "review", "reconcile", "takeover"]
    platform: Literal["douyin", "xiaohongshu", "bilibili", "wechat_official"]
    object_ref: dict[str, Any]
    instructions: str
    assigned_to: str | None = None


class ManualTaskReceipt(BaseModel):
    status: Literal["completed", "failed", "unknown"]
    receipt: dict[str, Any] = Field(default_factory=dict)


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
