"""Initial R0 schemas frozen at revision 0001."""

import sqlalchemy as sa
from alembic import op


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def versioned_columns():
    return (
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def upgrade():
    op.create_table(
        "organization_roles",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("profile_id", sa.String(40), nullable=False, unique=True),
        sa.Column("owner_role", sa.String(100), nullable=False),
        sa.Column("lifecycle", sa.String(30), nullable=False),
        sa.Column("manifest", sa.JSON(), nullable=False),
        *versioned_columns(),
    )
    op.create_table(
        "collaboration_events",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("correlation_id", sa.String(100), nullable=False),
        sa.Column("created_by", sa.String(120), nullable=False),
        *versioned_columns(),
    )
    op.create_table(
        "collaboration_commitments",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("proposed_role", sa.String(80), nullable=False),
        sa.Column("committed_role", sa.String(80)),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("acceptance", sa.JSON(), nullable=False),
        sa.Column("dependencies", sa.JSON(), nullable=False),
        sa.Column("context", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(120), nullable=False),
        *versioned_columns(),
    )
    op.create_table(
        "collaboration_handoffs",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("commitment_id", sa.String(80), nullable=False),
        sa.Column("sender_role", sa.String(80), nullable=False),
        sa.Column("recipient", sa.String(120), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        *versioned_columns(),
    )
    op.create_table(
        "governance_approvals",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("subject_type", sa.String(80), nullable=False),
        sa.Column("subject_id", sa.String(80), nullable=False),
        sa.Column("subject_version", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.Column("issued_by", sa.String(120), nullable=False),
        sa.Column("remaining_uses", sa.Integer(), nullable=False),
        *versioned_columns(),
    )
    op.create_table(
        "collaboration_agent_runs",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("hermes_run_id", sa.String(100)),
        sa.Column("commitment_id", sa.String(80), nullable=False),
        sa.Column("role_id", sa.String(80), nullable=False),
        sa.Column("profile_id", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("output", sa.JSON(), nullable=False),
        sa.Column("failure", sa.JSON(), nullable=False),
        sa.Column("correlation_id", sa.String(100), nullable=False),
        sa.Column("created_by", sa.String(120), nullable=False),
        *versioned_columns(),
    )
    op.create_table(
        "integration_manual_tasks",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("task_type", sa.String(60), nullable=False),
        sa.Column("platform", sa.String(40), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("object_ref", sa.JSON(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("receipt", sa.JSON(), nullable=False),
        sa.Column("assigned_to", sa.String(120)),
        *versioned_columns(),
    )
    op.create_table(
        "knowledge_items",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("kind", sa.String(60), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("source_refs", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(120), nullable=False),
        *versioned_columns(),
    )
    op.create_table(
        "knowledge_memory_entries",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("profile_id", sa.String(40), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("fact", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.String(300), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("active", sa.Boolean(), nullable=False),
        *versioned_columns(),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("actor_id", sa.String(120), nullable=False),
        sa.Column("actor_roles", sa.JSON(), nullable=False),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("resource_type", sa.String(80), nullable=False),
        sa.Column("resource_id", sa.String(100), nullable=False),
        sa.Column("correlation_id", sa.String(100), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "audit_idempotency",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("actor_id", sa.String(120), nullable=False),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(80), nullable=False),
        sa.Column("resource_id", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("actor_id", "idempotency_key", name="uq_actor_idempotency"),
    )
    op.create_table(
        "collaboration_outbox",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("aggregate_type", sa.String(80), nullable=False),
        sa.Column("aggregate_id", sa.String(100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    for table in (
        "collaboration_outbox", "audit_idempotency", "audit_logs", "knowledge_memory_entries",
        "knowledge_items", "integration_manual_tasks", "collaboration_agent_runs", "governance_approvals",
        "collaboration_handoffs", "collaboration_commitments", "collaboration_events", "organization_roles",
    ):
        op.drop_table(table)
