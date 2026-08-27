"""Compatibility marker for the existing local database revision."""

from alembic import op

revision = "2e61aabeeb93"
down_revision = "20260722_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
