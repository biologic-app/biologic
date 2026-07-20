"""add color to dashboard samples-by-status view

Revision ID: 20260714_0030
Revises: 20260714_0029
Create Date: 2026-07-14 00:30:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260714_0030"
down_revision = "20260714_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A materialized view cannot ALTER-ADD a column, so drop and recreate it with
    # the extra `status_color` column (the raw color name from sample_statuses).
    op.execute("DROP MATERIALIZED VIEW IF EXISTS dashboard_samples_by_status")
    op.execute(
        """
        CREATE MATERIALIZED VIEW dashboard_samples_by_status AS
        SELECT
            ss.code AS status_code,
            ss.name AS status_name,
            ss.color AS status_color,
            count(s.id)::int AS count,
            statement_timestamp() AS refreshed_at
        FROM sample_statuses ss
        LEFT JOIN samples s ON s.status_id = ss.id AND s.deleted_at IS NULL
        WHERE ss.deleted_at IS NULL
        GROUP BY ss.code, ss.name, ss.color
        """
    )
    # Unique index is required for REFRESH MATERIALIZED VIEW ... CONCURRENTLY.
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS dashboard_samples_by_status_code
        ON dashboard_samples_by_status (status_code)
        """
    )


def downgrade() -> None:
    # Restore the prior shape exactly (no status_color column).
    op.execute("DROP MATERIALIZED VIEW IF EXISTS dashboard_samples_by_status")
    op.execute(
        """
        CREATE MATERIALIZED VIEW dashboard_samples_by_status AS
        SELECT
            ss.code AS status_code,
            ss.name AS status_name,
            count(s.id)::int AS count,
            statement_timestamp() AS refreshed_at
        FROM sample_statuses ss
        LEFT JOIN samples s ON s.status_id = ss.id AND s.deleted_at IS NULL
        WHERE ss.deleted_at IS NULL
        GROUP BY ss.code, ss.name
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS dashboard_samples_by_status_code
        ON dashboard_samples_by_status (status_code)
        """
    )
