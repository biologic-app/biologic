"""assign existing unscoped users to the central branch

Revision ID: 20260902_0040
Revises: 20260902_0039
Create Date: 2026-09-02 09:20:00.000000
"""

from alembic import op

revision = "20260902_0040"
down_revision = "20260902_0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # BR-CENTRAL is the seeded ЦББ branch. Keep this idempotent so existing
    # assignments are preserved while previously unscoped users are repaired.
    op.execute(
        """
        UPDATE users AS u
        SET branch_id = b.id, updated_at = CURRENT_TIMESTAMP
        FROM branches AS b
        WHERE b.code = 'BR-CENTRAL'
          AND u.branch_id IS NULL
        """
    )


def downgrade() -> None:
    # Do not remove assignments made intentionally after this migration.
    pass
