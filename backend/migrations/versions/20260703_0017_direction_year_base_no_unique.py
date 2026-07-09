"""add unique partial index on directions (year_no, base_no)

Revision ID: 20260703_0017
Revises: 20260702_0016
Create Date: 2026-07-03 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260703_0017"
down_revision = "20260702_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # CONCURRENTLY requires an autocommit block (outside transaction).
    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS
            directions_directions_year_no_base_no
            ON directions (year_no, base_no)
            WHERE deleted_at IS NULL
            """
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "DROP INDEX CONCURRENTLY IF EXISTS directions_directions_year_no_base_no"
        )
