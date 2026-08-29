import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
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
    profile_version: Mapped[int | None] = mapped_column(Integer)
    profile_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    execution_mode: Mapped[str | None] = mapped_column(String(20))
    case_id: Mapped[str | None] = mapped_column(String(80), index=True)
    stage_key: Mapped[str | None] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(40), default="queued", nullable=False)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    output: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    failure: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    created_by: Mapped[str] = mapped_column(String(120), nullable=False)
    current_attempt_id: Mapped[str | None] = mapped_column(String(80))
    cancellation_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    traceparent: Mapped[str | None] = mapped_column(String(128))
    tracestate: Mapped[str | None] = mapped_column(String(512))
    transition_seq: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class AgentRunAttempt(Base):
    __tablename__ = "collaboration_agent_run_attempts"
    __table_args__ = (UniqueConstraint("run_id", "attempt_no", name="uq_run_attempt_no"),)
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: new_id("attempt"))
    run_id: Mapped[str] = mapped_column(ForeignKey("collaboration_agent_runs.id"), nullable=False, index=True)
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="claimed", nullable=False)
    worker_id: Mapped[str] = mapped_column(String(160), nullable=False)
    lease_token: Mapped[str] = mapped_column(String(80), nullable=False)
    lease_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    hermes_run_id: Mapped[str | None] = mapped_column(String(100))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    output: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    failure: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    failure_class: Mapped[str | None] = mapped_column(String(80))
    retryability: Mapped[str] = mapped_column(String(20), default="conditional", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now, nullable=False)


class AgentRunTransition(Base):
    __tablename__ = "collaboration_agent_run_transitions"
    __table_args__ = (UniqueConstraint("run_id", "sequence_no", name="uq_run_transition_sequence"),)
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: new_id("transition"))
    run_id: Mapped[str] = mapped_column(ForeignKey("collaboration_agent_runs.id"), nullable=False, index=True)
    attempt_id: Mapped[str | None] = mapped_column(String(80))
    from_status: Mapped[str] = mapped_column(String(40), nullable=False)
    to_status: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str] = mapped_column(String(240), nullable=False)
    actor: Mapped[str] = mapped_column(String(160), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)


class MarketingCase(Base, VersionedMixin):
    __tablename__ = "marketing_cases"
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: new_id("case"))
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    target_platform: Mapped[str] = mapped_column(String(40), nullable=False)
    execution_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)
    current_stage: Mapped[str] = mapped_column(String(60), default="mo_plan", nullable=False)
    created_by: Mapped[str] = mapped_column(String(120), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)


class MarketingDeliverable(Base, VersionedMixin):
    __tablename__ = "marketing_case_deliverables"
    __table_args__ = (UniqueConstraint("case_id", name="uq_marketing_deliverable_case"),)
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: new_id("deliverable"))
    case_id: Mapped[str] = mapped_column(ForeignKey("marketing_cases.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    format_version: Mapped[str] = mapped_column(String(40), default="marketing-plan/v1", nullable=False)
    document_json: Mapped[dict] = mapped_column("document", JSON, default=dict, nullable=False)
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    source_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_by: Mapped[str] = mapped_column(String(120), nullable=False)
    accepted_by: Mapped[str | None] = mapped_column(String(120))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MarketingDeliverableRevision(Base):
    __tablename__ = "marketing_case_deliverable_revisions"
    __table_args__ = (UniqueConstraint("deliverable_id", "version_no", name="uq_marketing_deliverable_revision"),)
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: new_id("deliverable_rev"))
    deliverable_id: Mapped[str] = mapped_column(ForeignKey("marketing_case_deliverables.id"), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("marketing_cases.id"), nullable=False, index=True)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    document_json: Mapped[dict] = mapped_column("document", JSON, default=dict, nullable=False)
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    source_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)


class MarketingCaseStep(Base):
    __tablename__ = "marketing_case_steps"
    __table_args__ = (UniqueConstraint("case_id", "step_key", name="uq_marketing_case_step"),)
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: new_id("case_step"))
    case_id: Mapped[str] = mapped_column(ForeignKey("marketing_cases.id"), nullable=False, index=True)
    step_key: Mapped[str] = mapped_column(String(60), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    commitment_id: Mapped[str | None] = mapped_column(ForeignKey("collaboration_commitments.id"))
    active_run_id: Mapped[str | None] = mapped_column(ForeignKey("collaboration_agent_runs.id"))
    input: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    output: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    failure: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now, nullable=False)


class MarketingCaseResource(Base):
    __tablename__ = "marketing_case_resources"
    __table_args__ = (
        UniqueConstraint(
            "case_id", "resource_type", "resource_id", "relation",
            name="uq_marketing_case_resource",
        ),
    )
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: new_id("case_ref"))
    case_id: Mapped[str] = mapped_column(ForeignKey("marketing_cases.id"), nullable=False, index=True)
    step_id: Mapped[str | None] = mapped_column(ForeignKey("marketing_case_steps.id"))
    resource_type: Mapped[str] = mapped_column(String(60), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_version: Mapped[int | None] = mapped_column(Integer)
    relation: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)


class MarketingCaseMessage(Base):
    __tablename__ = "marketing_case_messages"
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: new_id("case_msg"))
    case_id: Mapped[str] = mapped_column(ForeignKey("marketing_cases.id"), nullable=False, index=True)
    stage_key: Mapped[str | None] = mapped_column(String(60))
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False)
    intent: Mapped[str] = mapped_column(String(40), default="message", nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    attachments: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_by: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)


class MarketingDecision(Base):
    __tablename__ = "marketing_case_decisions"
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: new_id("case_decision"))
    case_id: Mapped[str] = mapped_column(ForeignKey("marketing_cases.id"), nullable=False, index=True)
    stage_key: Mapped[str] = mapped_column(String(60), nullable=False)
    decision: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    subject_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
    actor_id: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)


class MarketingReconciliation(Base):
    __tablename__ = "marketing_case_reconciliations"
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: new_id("reconcile"))
    case_id: Mapped[str] = mapped_column(ForeignKey("marketing_cases.id"), nullable=False, index=True)
    step_id: Mapped[str] = mapped_column(ForeignKey("marketing_case_steps.id"), nullable=False)
    run_id: Mapped[str | None] = mapped_column(String(80))
    attempt_id: Mapped[str | None] = mapped_column(String(80))
    resolution: Mapped[str] = mapped_column(String(40), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    actor_id: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)


class AgentProfileConfig(Base, VersionedMixin):
    __tablename__ = "agent_profile_configs"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    agent_key: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="published", nullable=False)
    published_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    config_json: Mapped[dict] = mapped_column("config", JSON, default=dict, nullable=False)
    updated_by: Mapped[str] = mapped_column(String(120), nullable=False)


class AgentProfileRevision(Base):
    __tablename__ = "agent_profile_revisions"
    __table_args__ = (UniqueConstraint("agent_key", "version_no", name="uq_agent_profile_revision"),)
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: new_id("profile_rev"))
    agent_key: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    config_json: Mapped[dict] = mapped_column("config", JSON, default=dict, nullable=False)
    summary: Mapped[str] = mapped_column(String(240), nullable=False)
    created_by: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)


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
