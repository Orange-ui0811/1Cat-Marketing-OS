"""Add unified workspace activity, change requests, chat turns and object lineage."""

import sqlalchemy as sa
from alembic import op


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "collaboration_agent_runs",
        sa.Column("purpose", sa.String(30), nullable=False, server_default="workflow"),
    )

    with op.batch_alter_table("knowledge_items") as batch_op:
        batch_op.add_column(sa.Column("lineage_id", sa.String(80), nullable=True))
        batch_op.add_column(sa.Column("revision_no", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("supersedes_id", sa.String(80), nullable=True))
        batch_op.add_column(sa.Column("generated_by_run_id", sa.String(80), nullable=True))
        batch_op.create_foreign_key(
            "fk_knowledge_items_supersedes_id",
            "knowledge_items",
            ["supersedes_id"],
            ["id"],
        )
    op.execute("UPDATE knowledge_items SET lineage_id = id, revision_no = version")
    with op.batch_alter_table("knowledge_items") as batch_op:
        batch_op.alter_column("lineage_id", existing_type=sa.String(80), nullable=False)
        batch_op.alter_column("revision_no", existing_type=sa.Integer(), nullable=False)
        batch_op.create_index("ix_knowledge_items_lineage_id", ["lineage_id"])
        batch_op.create_index("ix_knowledge_items_generated_by_run_id", ["generated_by_run_id"])
        batch_op.create_unique_constraint(
            "uq_knowledge_lineage_revision",
            ["lineage_id", "revision_no"],
        )

    op.create_table(
        "marketing_case_change_requests",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("case_id", sa.String(80), sa.ForeignKey("marketing_cases.id"), nullable=False),
        sa.Column("stage_key", sa.String(60), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("summary", sa.String(240), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("target_refs", sa.JSON(), nullable=False),
        sa.Column("proposed_change", sa.JSON(), nullable=False),
        sa.Column("resolution", sa.JSON(), nullable=False),
        sa.Column("requested_by", sa.String(120), nullable=False),
        sa.Column("resolved_by", sa.String(120)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("result_run_id", sa.String(80)),
        sa.Column("result_object_refs", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_marketing_case_change_requests_case_id", "marketing_case_change_requests", ["case_id"])

    op.create_table(
        "marketing_case_activities",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("case_id", sa.String(80), sa.ForeignKey("marketing_cases.id"), nullable=False),
        sa.Column("stage_key", sa.String(60)),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("actor_id", sa.String(120), nullable=False),
        sa.Column("summary", sa.String(300), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.Column("resource_refs", sa.JSON(), nullable=False),
        sa.Column("correlation_id", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_marketing_case_activities_case_id", "marketing_case_activities", ["case_id"])

    op.create_table(
        "marketing_chat_turns",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("case_id", sa.String(80), sa.ForeignKey("marketing_cases.id"), nullable=False),
        sa.Column("stage_key", sa.String(60)),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("user_message_id", sa.String(80), sa.ForeignKey("marketing_case_messages.id"), nullable=False),
        sa.Column("agent_message_id", sa.String(80), sa.ForeignKey("marketing_case_messages.id")),
        sa.Column("run_id", sa.String(80), sa.ForeignKey("collaboration_agent_runs.id")),
        sa.Column("profile_id", sa.String(40)),
        sa.Column("profile_version", sa.Integer()),
        sa.Column("profile_hash", sa.String(64)),
        sa.Column("execution_mode", sa.String(20), nullable=False),
        sa.Column("failure", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_marketing_chat_turns_case_id", "marketing_chat_turns", ["case_id"])


def downgrade():
    op.drop_index("ix_marketing_chat_turns_case_id", table_name="marketing_chat_turns")
    op.drop_table("marketing_chat_turns")
    op.drop_index("ix_marketing_case_activities_case_id", table_name="marketing_case_activities")
    op.drop_table("marketing_case_activities")
    op.drop_index("ix_marketing_case_change_requests_case_id", table_name="marketing_case_change_requests")
    op.drop_table("marketing_case_change_requests")
    with op.batch_alter_table("knowledge_items") as batch_op:
        batch_op.drop_constraint("uq_knowledge_lineage_revision", type_="unique")
        batch_op.drop_index("ix_knowledge_items_generated_by_run_id")
        batch_op.drop_index("ix_knowledge_items_lineage_id")
        batch_op.drop_constraint("fk_knowledge_items_supersedes_id", type_="foreignkey")
        batch_op.drop_column("generated_by_run_id")
        batch_op.drop_column("supersedes_id")
        batch_op.drop_column("revision_no")
        batch_op.drop_column("lineage_id")
    op.drop_column("collaboration_agent_runs", "purpose")
