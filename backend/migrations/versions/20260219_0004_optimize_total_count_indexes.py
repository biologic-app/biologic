"""add partial indexes to optimize total count on high-load tables

Revision ID: 20260219_0004
Revises: 20260219_0003
Create Date: 2026-02-19 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260219_0004"
down_revision = "20260219_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # CONCURRENTLY requires an autocommit block.
    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS research_research_active_id
            ON research (id)
            WHERE deleted_at IS NULL
            """
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS tests_tests_active_id
            ON tests (id)
            WHERE deleted_at IS NULL
            """
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS tests_tests_active_id")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS research_research_active_id")
