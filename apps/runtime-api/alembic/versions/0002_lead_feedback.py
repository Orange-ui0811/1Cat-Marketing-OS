"""Add PII-free lead stubs and immutable sales feedback."""

import sqlalchemy as sa
from alembic import op


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "integration_lead_stubs",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("source_record_ref", sa.String(300), nullable=False),
        sa.Column("touchpoint", sa.String(80), nullable=False),
        sa.Column("campaign_ref", sa.String(160)),
        sa.Column("content_ref", sa.String(160)),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_by", sa.String(120), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "integration_sales_feedback",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("lead_stub_id", sa.String(80), nullable=False),
        sa.Column("lead_version", sa.Integer(), nullable=False),
        sa.Column("inquiry_status", sa.String(40), nullable=False),
        sa.Column("reason_code", sa.String(80), nullable=False),
        sa.Column("registry_version", sa.String(40), nullable=False),
        sa.Column("sales_actor_id", sa.String(120), nullable=False),
        sa.Column("correlation_id", sa.String(100), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("integration_sales_feedback")
    op.drop_table("integration_lead_stubs")
