"""Add PII-free lead stubs and immutable sales feedback."""
from alembic import op

from app.db import Base
from app import models  # noqa: F401

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    Base.metadata.tables["integration_lead_stubs"].create(bind=op.get_bind(), checkfirst=True)
    Base.metadata.tables["integration_sales_feedback"].create(bind=op.get_bind(), checkfirst=True)


def downgrade():
    Base.metadata.tables["integration_sales_feedback"].drop(bind=op.get_bind(), checkfirst=True)
    Base.metadata.tables["integration_lead_stubs"].drop(bind=op.get_bind(), checkfirst=True)
