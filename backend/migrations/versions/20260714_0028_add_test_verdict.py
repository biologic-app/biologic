"""add verdict column to tests

Revision ID: 20260714_0028
Revises: 20260713_0027
Create Date: 2026-07-14 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260714_0028"
down_revision = "20260713_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE tests
          ADD COLUMN IF NOT EXISTS verdict boolean
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE tests DROP COLUMN IF EXISTS verdict")
