"""dashboard materialized views

Revision ID: 20260603_0013
Revises: 20260602_0012
Create Date: 2026-06-03 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260603_0013"
down_revision = "20260602_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS dashboard_workflow_daily AS
        WITH days AS (
            SELECT date_trunc('day', received_at)::date AS bucket_date
            FROM directions
            WHERE deleted_at IS NULL AND received_at IS NOT NULL
            UNION
            SELECT date_trunc('day', received_at)::date
            FROM samples
            WHERE deleted_at IS NULL AND received_at IS NOT NULL
            UNION
            SELECT date_trunc('day', completed_at)::date
            FROM samples
            WHERE deleted_at IS NULL AND completed_at IS NOT NULL
            UNION
            SELECT date_trunc('day', s.updated_at)::date
            FROM samples s
            JOIN sample_statuses ss ON ss.id = s.status_id
            WHERE s.deleted_at IS NULL AND ss.code = 'rejected'
            UNION
            SELECT date_trunc('day', completed_at)::date
            FROM research
            WHERE deleted_at IS NULL AND completed_at IS NOT NULL
            UNION
            SELECT date_trunc('day', t.updated_at)::date
            FROM tests t
            JOIN test_statuses ts ON ts.id = t.status_id
            WHERE t.deleted_at IS NULL AND ts.code IN ('completed', 'rejected')
            UNION
            SELECT date_trunc('day', issued_at)::date
            FROM protocols
            WHERE deleted_at IS NULL AND issued_at IS NOT NULL
        )
        SELECT
            days.bucket_date,
            (
                SELECT count(*)::int
                FROM directions d
                WHERE d.deleted_at IS NULL
                  AND d.received_at IS NOT NULL
                  AND date_trunc('day', d.received_at)::date = days.bucket_date
            ) AS directions_received,
            (
                SELECT count(*)::int
                FROM samples s
                WHERE s.deleted_at IS NULL
                  AND s.received_at IS NOT NULL
                  AND date_trunc('day', s.received_at)::date = days.bucket_date
            ) AS samples_received,
            (
                SELECT count(*)::int
                FROM samples s
                WHERE s.deleted_at IS NULL
                  AND s.completed_at IS NOT NULL
                  AND date_trunc('day', s.completed_at)::date = days.bucket_date
            ) AS samples_completed,
            (
                SELECT count(*)::int
                FROM samples s
                JOIN sample_statuses ss ON ss.id = s.status_id
                WHERE s.deleted_at IS NULL
                  AND ss.code = 'rejected'
                  AND date_trunc('day', s.updated_at)::date = days.bucket_date
            ) AS samples_rejected,
            (
                SELECT count(*)::int
                FROM research r
                WHERE r.deleted_at IS NULL
                  AND r.completed_at IS NOT NULL
                  AND date_trunc('day', r.completed_at)::date = days.bucket_date
            ) AS research_completed,
            (
                SELECT count(*)::int
                FROM tests t
                JOIN test_statuses ts ON ts.id = t.status_id
                WHERE t.deleted_at IS NULL
                  AND ts.code = 'completed'
                  AND date_trunc('day', t.updated_at)::date = days.bucket_date
            ) AS tests_completed,
            (
                SELECT count(*)::int
                FROM tests t
                JOIN test_statuses ts ON ts.id = t.status_id
                WHERE t.deleted_at IS NULL
                  AND ts.code = 'rejected'
                  AND date_trunc('day', t.updated_at)::date = days.bucket_date
            ) AS tests_rejected,
            (
                SELECT count(*)::int
                FROM protocols p
                WHERE p.deleted_at IS NULL
                  AND p.issued_at IS NOT NULL
                  AND date_trunc('day', p.issued_at)::date = days.bucket_date
            ) AS protocols_issued,
            statement_timestamp() AS refreshed_at
        FROM days
        WHERE days.bucket_date IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS dashboard_workflow_daily_bucket_date
        ON dashboard_workflow_daily (bucket_date)
        """
    )

    op.execute(
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS dashboard_workflow_current AS
        SELECT
            1 AS row_key,
            statement_timestamp() AS refreshed_at,
            (
                SELECT count(*)::int
                FROM directions
                WHERE deleted_at IS NULL
            ) AS directions_total,
            (
                SELECT count(*)::int
                FROM directions d
                JOIN direction_statuses ds ON ds.id = d.status_id
                WHERE d.deleted_at IS NULL
                  AND d.is_urgent IS TRUE
                  AND ds.code <> 'completed'
            ) AS directions_urgent_open,
            (
                SELECT count(*)::int
                FROM samples
                WHERE deleted_at IS NULL
            ) AS samples_total,
            (
                SELECT count(*)::int
                FROM samples
                WHERE deleted_at IS NULL
                  AND received_at IS NOT NULL
            ) AS samples_received_total,
            (
                SELECT count(*)::int
                FROM samples s
                JOIN sample_statuses ss ON ss.id = s.status_id
                WHERE s.deleted_at IS NULL
                  AND ss.code = 'completed'
            ) AS samples_completed_total,
            (
                SELECT count(*)::int
                FROM samples s
                JOIN sample_statuses ss ON ss.id = s.status_id
                WHERE s.deleted_at IS NULL
                  AND ss.code = 'rejected'
            ) AS samples_rejected_total,
            (
                SELECT count(*)::int
                FROM samples s
                LEFT JOIN sample_statuses ss ON ss.id = s.status_id
                WHERE s.deleted_at IS NULL
                  AND COALESCE(ss.code, '') NOT IN ('completed', 'rejected')
            ) AS samples_open_total,
            (
                SELECT count(*)::int
                FROM samples s
                LEFT JOIN sample_statuses ss ON ss.id = s.status_id
                WHERE s.deleted_at IS NULL
                  AND s.deadline IS NOT NULL
                  AND s.deadline < statement_timestamp()
                  AND COALESCE(ss.code, '') NOT IN ('completed', 'rejected')
            ) AS samples_overdue_open,
            (
                SELECT count(*)::int
                FROM samples s
                LEFT JOIN sample_statuses ss ON ss.id = s.status_id
                WHERE s.deleted_at IS NULL
                  AND s.is_urgent IS TRUE
                  AND COALESCE(ss.code, '') NOT IN ('completed', 'rejected')
            ) AS samples_urgent_open,
            (
                SELECT count(*)::int
                FROM research r
                JOIN research_statuses rs ON rs.id = r.status_id
                WHERE r.deleted_at IS NULL
                  AND rs.code IN ('ordered', 'in_progress')
            ) AS research_active_total,
            (
                SELECT count(*)::int
                FROM tests t
                JOIN test_statuses ts ON ts.id = t.status_id
                WHERE t.deleted_at IS NULL
                  AND t.is_active IS TRUE
                  AND ts.code = 'queued'
            ) AS tests_queued_total,
            (
                SELECT count(*)::int
                FROM tests t
                JOIN test_statuses ts ON ts.id = t.status_id
                WHERE t.deleted_at IS NULL
                  AND t.is_active IS TRUE
                  AND ts.code = 'in_progress'
            ) AS tests_in_progress_total,
            (
                SELECT count(*)::int
                FROM tests t
                JOIN test_statuses ts ON ts.id = t.status_id
                WHERE t.deleted_at IS NULL
                  AND t.is_active IS TRUE
                  AND ts.code = 'completed'
            ) AS tests_completed_total,
            (
                SELECT count(*)::int
                FROM protocols
                WHERE deleted_at IS NULL
                  AND issued_at IS NOT NULL
            ) AS protocols_issued_total,
            COALESCE((
                SELECT round(avg(extract(epoch FROM (s.completed_at - s.received_at)) / 60))::int
                FROM samples s
                WHERE s.deleted_at IS NULL
                  AND s.received_at IS NOT NULL
                  AND s.completed_at IS NOT NULL
                  AND s.completed_at >= s.received_at
            ), 0) AS avg_sample_turnaround_minutes
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS dashboard_workflow_current_row_key
        ON dashboard_workflow_current (row_key)
        """
    )

    op.execute(
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS dashboard_samples_by_status AS
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

    op.execute(
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS dashboard_research_by_lab AS
        SELECT
            r.lab_id,
            COALESCE(l.name, 'Без лаборатории') AS lab_name,
            count(*) FILTER (WHERE rs.code IN ('ordered', 'in_progress'))::int AS active_count,
            count(*) FILTER (WHERE rs.code = 'completed')::int AS completed_count,
            statement_timestamp() AS refreshed_at
        FROM research r
        LEFT JOIN labs l ON l.id = r.lab_id
        LEFT JOIN research_statuses rs ON rs.id = r.status_id
        WHERE r.deleted_at IS NULL
        GROUP BY r.lab_id, l.name
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS dashboard_research_by_lab_lab_id
        ON dashboard_research_by_lab (lab_id)
        """
    )

    op.execute(
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS dashboard_sample_type_daily AS
        SELECT
            date_trunc('day', COALESCE(s.received_at, s.created_at))::date AS bucket_date,
            s.sample_type_id,
            COALESCE(st.name, 'Без типа') AS sample_type_name,
            count(*)::int AS count,
            statement_timestamp() AS refreshed_at
        FROM samples s
        LEFT JOIN sample_types st ON st.id = s.sample_type_id
        WHERE s.deleted_at IS NULL
        GROUP BY bucket_date, s.sample_type_id, st.name
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS dashboard_sample_type_daily_bucket_date
        ON dashboard_sample_type_daily (bucket_date)
        """
    )


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS dashboard_sample_type_daily")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS dashboard_research_by_lab")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS dashboard_samples_by_status")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS dashboard_workflow_current")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS dashboard_workflow_daily")
