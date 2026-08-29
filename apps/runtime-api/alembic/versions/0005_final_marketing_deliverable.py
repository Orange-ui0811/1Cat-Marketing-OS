"""Add the persisted final marketing-plan deliverable."""

import sqlalchemy as sa
from alembic import op


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "marketing_case_deliverables",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("case_id", sa.String(80), sa.ForeignKey("marketing_cases.id"), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("format_version", sa.String(40), nullable=False),
        sa.Column("document", sa.JSON, nullable=False),
        sa.Column("markdown", sa.Text, nullable=False),
        sa.Column("source_refs", sa.JSON, nullable=False),
        sa.Column("created_by", sa.String(120), nullable=False),
        sa.Column("accepted_by", sa.String(120)),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("case_id", name="uq_marketing_deliverable_case"),
    )
    op.create_index(
        "ix_marketing_case_deliverables_case_id",
        "marketing_case_deliverables",
        ["case_id"],
    )


def downgrade():
    op.drop_index("ix_marketing_case_deliverables_case_id", table_name="marketing_case_deliverables")
    op.drop_table("marketing_case_deliverables")
