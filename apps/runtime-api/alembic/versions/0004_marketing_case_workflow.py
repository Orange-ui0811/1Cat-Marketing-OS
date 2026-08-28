"""Add the persisted three-agent marketing case workflow."""

import sqlalchemy as sa
from alembic import op


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("collaboration_agent_runs", sa.Column("execution_mode", sa.String(20)))
    op.add_column("collaboration_agent_runs", sa.Column("case_id", sa.String(80)))
    op.add_column("collaboration_agent_runs", sa.Column("stage_key", sa.String(60)))
    op.create_index("ix_collaboration_agent_runs_case_id", "collaboration_agent_runs", ["case_id"])

    op.create_table(
        "marketing_cases",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("objective", sa.Text, nullable=False),
        sa.Column("target_platform", sa.String(40), nullable=False),
        sa.Column("execution_mode", sa.String(20), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("current_stage", sa.String(60), nullable=False),
        sa.Column("created_by", sa.String(120), nullable=False),
        sa.Column("correlation_id", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "marketing_case_steps",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("case_id", sa.String(80), sa.ForeignKey("marketing_cases.id"), nullable=False),
        sa.Column("step_key", sa.String(60), nullable=False),
        sa.Column("ordinal", sa.Integer, nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("commitment_id", sa.String(80), sa.ForeignKey("collaboration_commitments.id")),
        sa.Column("active_run_id", sa.String(80), sa.ForeignKey("collaboration_agent_runs.id")),
        sa.Column("input", sa.JSON, nullable=False),
        sa.Column("output", sa.JSON, nullable=False),
        sa.Column("failure", sa.JSON, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("case_id", "step_key", name="uq_marketing_case_step"),
    )
    op.create_index("ix_marketing_case_steps_case_id", "marketing_case_steps", ["case_id"])
    op.create_table(
        "marketing_case_resources",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("case_id", sa.String(80), sa.ForeignKey("marketing_cases.id"), nullable=False),
        sa.Column("step_id", sa.String(80), sa.ForeignKey("marketing_case_steps.id")),
        sa.Column("resource_type", sa.String(60), nullable=False),
        sa.Column("resource_id", sa.String(80), nullable=False),
        sa.Column("resource_version", sa.Integer),
        sa.Column("relation", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "case_id", "resource_type", "resource_id", "relation",
            name="uq_marketing_case_resource",
        ),
    )
    op.create_index("ix_marketing_case_resources_case_id", "marketing_case_resources", ["case_id"])


def downgrade():
    op.drop_index("ix_marketing_case_resources_case_id", table_name="marketing_case_resources")
    op.drop_table("marketing_case_resources")
    op.drop_index("ix_marketing_case_steps_case_id", table_name="marketing_case_steps")
    op.drop_table("marketing_case_steps")
    op.drop_table("marketing_cases")
    op.drop_index("ix_collaboration_agent_runs_case_id", table_name="collaboration_agent_runs")
    op.drop_column("collaboration_agent_runs", "stage_key")
    op.drop_column("collaboration_agent_runs", "case_id")
    op.drop_column("collaboration_agent_runs", "execution_mode")
