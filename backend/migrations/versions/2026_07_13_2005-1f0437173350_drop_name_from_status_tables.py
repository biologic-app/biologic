"""drop name from status tables

Revision ID: 1f0437173350
Revises: 20260714_0030
Create Date: 2026-07-13 20:05:39.282892
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1f0437173350"
down_revision = "20260714_0030"
branch_labels = None
depends_on = None

_STATUS_TABLES = (
    "direction_statuses",
    "sample_statuses",
    "research_statuses",
    "test_statuses",
)


def upgrade() -> None:
    # The `dashboard_samples_by_status` materialized view selects
    # `sample_statuses.name`, so it must be dropped before the column can go and
    # recreated without it (a materialized view cannot ALTER-DROP a column).
    op.execute("DROP MATERIALIZED VIEW IF EXISTS dashboard_samples_by_status")

    for table in _STATUS_TABLES:
        op.drop_column(table, "name")

    op.execute(
        """
        CREATE MATERIALIZED VIEW dashboard_samples_by_status AS
        SELECT
            ss.code AS status_code,
            ss.color AS status_color,
            count(s.id)::int AS count,
            statement_timestamp() AS refreshed_at
        FROM sample_statuses ss
        LEFT JOIN samples s ON s.status_id = ss.id AND s.deleted_at IS NULL
        WHERE ss.deleted_at IS NULL
        GROUP BY ss.code, ss.color
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
    # `name` is re-added nullable: the original values are lost on the drop, so
    # they cannot be restored here.
    for table in _STATUS_TABLES:
        op.add_column(table, sa.Column("name", sa.Text(), nullable=True))

    # Restore the view shape from 20260714_0030 (with status_name).
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
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS dashboard_samples_by_status_code
        ON dashboard_samples_by_status (status_code)
        """
    )
