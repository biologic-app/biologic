"""enable pg_trgm for fuzzy search

Revision ID: 20260608_0014
Revises: 20260603_0013
Create Date: 2026-06-08 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260608_0014"
down_revision = "20260603_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
