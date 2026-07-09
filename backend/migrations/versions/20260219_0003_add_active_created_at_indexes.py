"""add partial indexes for active list ordering

Revision ID: 20260219_0003
Revises: 20260219_0002
Create Date: 2026-02-19 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260219_0003"
down_revision = "20260219_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # CONCURRENTLY requires an autocommit block (outside transaction).
    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS directions_directions_active_created_at
            ON directions (created_at DESC, id)
            WHERE deleted_at IS NULL
            """
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS samples_samples_active_created_at
            ON samples (created_at DESC, id)
            WHERE deleted_at IS NULL
            """
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS research_research_active_created_at
            ON research (created_at DESC, id)
            WHERE deleted_at IS NULL
            """
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS tests_tests_active_created_at
            ON tests (created_at DESC, id)
            WHERE deleted_at IS NULL
            """
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS tests_tests_active_created_at")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS research_research_active_created_at")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS samples_samples_active_created_at")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS directions_directions_active_created_at")
