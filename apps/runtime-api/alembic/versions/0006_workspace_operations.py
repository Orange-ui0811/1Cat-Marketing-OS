"""Add server-backed workspace collaboration, decisions, reconciliation and profiles."""

import sqlalchemy as sa
from alembic import op


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "collaboration_agent_runs",
        sa.Column("profile_version", sa.Integer),
    )
    op.add_column(
        "collaboration_agent_runs",
        sa.Column("profile_snapshot", sa.JSON, nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_table(
        "marketing_case_messages",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("case_id", sa.String(80), sa.ForeignKey("marketing_cases.id"), nullable=False),
        sa.Column("stage_key", sa.String(60)),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("sender_type", sa.String(20), nullable=False),
        sa.Column("intent", sa.String(40), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("attachments", sa.JSON, nullable=False),
        sa.Column("created_by", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_marketing_case_messages_case_id", "marketing_case_messages", ["case_id"])

    op.create_table(
        "marketing_case_decisions",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("case_id", sa.String(80), sa.ForeignKey("marketing_cases.id"), nullable=False),
        sa.Column("stage_key", sa.String(60), nullable=False),
        sa.Column("decision", sa.String(40), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("subject_refs", sa.JSON, nullable=False),
        sa.Column("metadata", sa.JSON, nullable=False),
        sa.Column("actor_id", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_marketing_case_decisions_case_id", "marketing_case_decisions", ["case_id"])

    op.create_table(
        "marketing_case_reconciliations",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("case_id", sa.String(80), sa.ForeignKey("marketing_cases.id"), nullable=False),
        sa.Column("step_id", sa.String(80), sa.ForeignKey("marketing_case_steps.id"), nullable=False),
        sa.Column("run_id", sa.String(80)),
        sa.Column("attempt_id", sa.String(80)),
        sa.Column("resolution", sa.String(40), nullable=False),
        sa.Column("note", sa.Text, nullable=False),
        sa.Column("evidence", sa.JSON, nullable=False),
        sa.Column("actor_id", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_marketing_case_reconciliations_case_id", "marketing_case_reconciliations", ["case_id"])

    op.create_table(
        "marketing_case_deliverable_revisions",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("deliverable_id", sa.String(80), sa.ForeignKey("marketing_case_deliverables.id"), nullable=False),
        sa.Column("case_id", sa.String(80), sa.ForeignKey("marketing_cases.id"), nullable=False),
        sa.Column("version_no", sa.Integer, nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("document", sa.JSON, nullable=False),
        sa.Column("markdown", sa.Text, nullable=False),
        sa.Column("source_refs", sa.JSON, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_by", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("deliverable_id", "version_no", name="uq_marketing_deliverable_revision"),
    )
    op.create_index("ix_marketing_deliverable_revisions_deliverable_id", "marketing_case_deliverable_revisions", ["deliverable_id"])
    op.create_index("ix_marketing_deliverable_revisions_case_id", "marketing_case_deliverable_revisions", ["case_id"])

    op.create_table(
        "agent_profile_configs",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("agent_key", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("published_version", sa.Integer, nullable=False),
        sa.Column("config", sa.JSON, nullable=False),
        sa.Column("updated_by", sa.String(120), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("agent_key", name="uq_agent_profile_configs_agent_key"),
    )
    op.create_index("ix_agent_profile_configs_agent_key", "agent_profile_configs", ["agent_key"])

    op.create_table(
        "agent_profile_revisions",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("agent_key", sa.String(20), nullable=False),
        sa.Column("version_no", sa.Integer, nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("config", sa.JSON, nullable=False),
        sa.Column("summary", sa.String(240), nullable=False),
        sa.Column("created_by", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("agent_key", "version_no", name="uq_agent_profile_revision"),
    )
    op.create_index("ix_agent_profile_revisions_agent_key", "agent_profile_revisions", ["agent_key"])


def downgrade():
    op.drop_index("ix_agent_profile_revisions_agent_key", table_name="agent_profile_revisions")
    op.drop_table("agent_profile_revisions")
    op.drop_index("ix_agent_profile_configs_agent_key", table_name="agent_profile_configs")
    op.drop_table("agent_profile_configs")
    op.drop_index("ix_marketing_case_reconciliations_case_id", table_name="marketing_case_reconciliations")
    op.drop_table("marketing_case_reconciliations")
    op.drop_index("ix_marketing_deliverable_revisions_case_id", table_name="marketing_case_deliverable_revisions")
    op.drop_index("ix_marketing_deliverable_revisions_deliverable_id", table_name="marketing_case_deliverable_revisions")
    op.drop_table("marketing_case_deliverable_revisions")
    op.drop_index("ix_marketing_case_decisions_case_id", table_name="marketing_case_decisions")
    op.drop_table("marketing_case_decisions")
    op.drop_index("ix_marketing_case_messages_case_id", table_name="marketing_case_messages")
    op.drop_table("marketing_case_messages")
    op.drop_column("collaboration_agent_runs", "profile_snapshot")
    op.drop_column("collaboration_agent_runs", "profile_version")
