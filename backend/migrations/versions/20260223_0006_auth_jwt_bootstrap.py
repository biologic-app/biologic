"""add refresh token version column

Revision ID: 20260223_0006
Revises: 20260219_0005
Create Date: 2026-02-23 00:00:00.000000

This migration used to also seed the 'admin' role and 'admin' user as part of
auth bootstrap. That seed data is now owned by
``backend/scripts/seed_test_data.py`` (see ``ROLE_DEFINITIONS`` /
``SEED_USERS`` / ``_seed_bootstrap_data``), which is the sole seed source for
local/dev/test databases — run it once after ``alembic upgrade head``. Only
the structural column change remains here.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260223_0006"
down_revision = "20260219_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS refresh_token_version INTEGER NOT NULL DEFAULT 0
        """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE users
        DROP COLUMN IF EXISTS refresh_token_version
        """)
