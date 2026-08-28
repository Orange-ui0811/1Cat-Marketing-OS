"""Add recoverable Agent Runtime attempts and transition history."""

import sqlalchemy as sa
from alembic import op


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("collaboration_agent_runs", sa.Column("current_attempt_id", sa.String(80)))
    op.add_column("collaboration_agent_runs", sa.Column("cancellation_requested_at", sa.DateTime(timezone=True)))
    op.add_column("collaboration_agent_runs", sa.Column("started_at", sa.DateTime(timezone=True)))
    op.add_column("collaboration_agent_runs", sa.Column("completed_at", sa.DateTime(timezone=True)))
    op.add_column("collaboration_agent_runs", sa.Column("traceparent", sa.String(128)))
    op.add_column("collaboration_agent_runs", sa.Column("tracestate", sa.String(512)))
    op.add_column(
        "collaboration_agent_runs",
        sa.Column("transition_seq", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "collaboration_agent_run_attempts",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("run_id", sa.String(80), sa.ForeignKey("collaboration_agent_runs.id"), nullable=False),
        sa.Column("attempt_no", sa.Integer, nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("worker_id", sa.String(160), nullable=False),
        sa.Column("lease_token", sa.String(80), nullable=False),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hermes_run_id", sa.String(100)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("output", sa.JSON, nullable=False),
        sa.Column("failure", sa.JSON, nullable=False),
        sa.Column("failure_class", sa.String(80)),
        sa.Column("retryability", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id", "attempt_no", name="uq_run_attempt_no"),
    )
    op.create_index("ix_collaboration_agent_run_attempts_run_id", "collaboration_agent_run_attempts", ["run_id"])

    op.create_table(
        "collaboration_agent_run_transitions",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("run_id", sa.String(80), sa.ForeignKey("collaboration_agent_runs.id"), nullable=False),
        sa.Column("attempt_id", sa.String(80)),
        sa.Column("from_status", sa.String(40), nullable=False),
        sa.Column("to_status", sa.String(40), nullable=False),
        sa.Column("reason", sa.String(240), nullable=False),
        sa.Column("actor", sa.String(160), nullable=False),
        sa.Column("correlation_id", sa.String(100), nullable=False),
        sa.Column("sequence_no", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id", "sequence_no", name="uq_run_transition_sequence"),
    )
    op.create_index("ix_collaboration_agent_run_transitions_run_id", "collaboration_agent_run_transitions", ["run_id"])


def downgrade():
    op.drop_index("ix_collaboration_agent_run_transitions_run_id", table_name="collaboration_agent_run_transitions")
    op.drop_table("collaboration_agent_run_transitions")
    op.drop_index("ix_collaboration_agent_run_attempts_run_id", table_name="collaboration_agent_run_attempts")
    op.drop_table("collaboration_agent_run_attempts")
    for column in (
        "transition_seq", "tracestate", "traceparent", "completed_at", "started_at",
        "cancellation_requested_at", "current_attempt_id",
    ):
        op.drop_column("collaboration_agent_runs", column)
