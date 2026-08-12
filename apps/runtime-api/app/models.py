import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


class VersionedMixin:
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now, nullable=False)


class Role(Base, VersionedMixin):
    __tablename__ = "organization_roles"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    profile_id: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    owner_role: Mapped[str] = mapped_column(String(100), nullable=False)
    lifecycle: Mapped[str] = mapped_column(String(30), default="defined", nullable=False)
    manifest: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class OrganizationEvent(Base, VersionedMixin):
    __tablename__ = "collaboration_events"
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: new_id("evt"))
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    created_by: Mapped[str] = mapped_column(String(120), nullable=False)


class Commitment(Base, VersionedMixin):
    __tablename__ = "collaboration_commitments"
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: new_id("wc"))
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="proposed", nullable=False)
    proposed_role: Mapped[str] = mapped_column(String(80), nullable=False)
    committed_role: Mapped[str | None] = mapped_column(String(80))
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    acceptance: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    dependencies: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    context: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_by: Mapped[str] = mapped_column(String(120), nullable=False)


class Handoff(Base, VersionedMixin):
    __tablename__ = "collaboration_handoffs"
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: new_id("handoff"))
    commitment_id: Mapped[str] = mapped_column(String(80), nullable=False)
    sender_role: Mapped[str] = mapped_column(String(80), nullable=False)
    recipient: Mapped[str] = mapped_column(String(120), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class Approval(Base, VersionedMixin):
    __tablename__ = "governance_approvals"
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: new_id("grant"))
    subject_type: Mapped[str] = mapped_column(String(80), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(80), nullable=False)
    subject_version: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="issued", nullable=False)
    scope: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    issued_by: Mapped[str] = mapped_column(String(120), nullable=False)
    remaining_uses: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class AgentRun(Base, VersionedMixin):
    __tablename__ = "collaboration_agent_runs"
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: new_id("run"))
    hermes_run_id: Mapped[str | None] = mapped_column(String(100))
    commitment_id: Mapped[str] = mapped_column(String(80), nullable=False)
    role_id: Mapped[str] = mapped_column(String(80), nullable=False)
    profile_id: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="queued", nullable=False)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    output: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    failure: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    created_by: Mapped[str] = mapped_column(String(120), nullable=False)


class ManualTask(Base, VersionedMixin):
    __tablename__ = "integration_manual_tasks"
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: new_id("manual"))
    task_type: Mapped[str] = mapped_column(String(60), nullable=False)
    platform: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    object_ref: Mapped[dict] = mapped_column(JSON, nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    receipt: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    assigned_to: Mapped[str | None] = mapped_column(String(120))


class LeadStub(Base, VersionedMixin):
    __tablename__ = "integration_lead_stubs"
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: new_id("lead"))
    source_record_ref: Mapped[str] = mapped_column(String(300), nullable=False)
    touchpoint: Mapped[str] = mapped_column(String(80), nullable=False)
    campaign_ref: Mapped[str | None] = mapped_column(String(160))
    content_ref: Mapped[str | None] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(30), default="registered", nullable=False)
    created_by: Mapped[str] = mapped_column(String(120), nullable=False)


class SalesFeedback(Base):
    __tablename__ = "integration_sales_feedback"
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: new_id("salesfb"))
    lead_stub_id: Mapped[str] = mapped_column(String(80), nullable=False)
    lead_version: Mapped[int] = mapped_column(Integer, nullable=False)
    inquiry_status: Mapped[str] = mapped_column(String(40), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(80), nullable=False)
    registry_version: Mapped[str] = mapped_column(String(40), nullable=False)
    sales_actor_id: Mapped[str] = mapped_column(String(120), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)


class KnowledgeItem(Base, VersionedMixin):
    __tablename__ = "knowledge_items"
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: new_id("know"))
    kind: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="candidate", nullable=False)
    source_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
    created_by: Mapped[str] = mapped_column(String(120), nullable=False)


class MemoryEntry(Base, VersionedMixin):
    __tablename__ = "knowledge_memory_entries"
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: new_id("mem"))
    profile_id: Mapped[str] = mapped_column(String(40), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    fact: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str] = mapped_column(String(300), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: new_id("audit"))
    actor_id: Mapped[str] = mapped_column(String(120), nullable=False)
    actor_roles: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(100), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    detail: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)


class IdempotencyRecord(Base):
    __tablename__ = "audit_idempotency"
    __table_args__ = (UniqueConstraint("actor_id", "idempotency_key", name="uq_actor_idempotency"),)
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: new_id("idem"))
    actor_id: Mapped[str] = mapped_column(String(120), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)


class Outbox(Base):
    __tablename__ = "collaboration_outbox"
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: new_id("outbox"))
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(80), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
