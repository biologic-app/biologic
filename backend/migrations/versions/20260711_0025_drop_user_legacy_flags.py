"""drop legacy user role-shortcut flags

The is_registrar / is_lab_head / is_branch_head booleans were the old
single-target notification shortcut and a denormalised role hint. Role
association now lives in users.role_id and mandatory subscriptions in
role_subscription_rules, so these columns are dead.

Revision ID: 20260711_0025
Revises: 20260711_0024
Create Date: 2026-07-11 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260711_0025"
down_revision = "20260711_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE users
        DROP COLUMN IF EXISTS is_registrar,
        DROP COLUMN IF EXISTS is_lab_head,
        DROP COLUMN IF EXISTS is_branch_head;
        """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS is_registrar BOOLEAN,
        ADD COLUMN IF NOT EXISTS is_lab_head BOOLEAN,
        ADD COLUMN IF NOT EXISTS is_branch_head BOOLEAN;
        """)
