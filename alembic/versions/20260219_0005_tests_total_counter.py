"""add tests active total counter for fast list.total

Revision ID: 20260219_0005
Revises: 20260219_0004
Create Date: 2026-02-19 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260219_0005"
down_revision = "20260219_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS entity_active_counts (
            entity_name TEXT PRIMARY KEY,
            active_total BIGINT NOT NULL CHECK (active_total >= 0),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    op.execute(
        """
        INSERT INTO entity_active_counts (entity_name, active_total)
        VALUES ('tests', (SELECT COUNT(*) FROM tests WHERE deleted_at IS NULL))
        ON CONFLICT (entity_name) DO UPDATE
        SET
            active_total = EXCLUDED.active_total,
            updated_at = CURRENT_TIMESTAMP
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION sync_tests_active_total_row()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                IF NEW.deleted_at IS NULL THEN
                    UPDATE entity_active_counts
                    SET active_total = active_total + 1, updated_at = CURRENT_TIMESTAMP
                    WHERE entity_name = 'tests';
                END IF;
                RETURN NEW;
            ELSIF TG_OP = 'UPDATE' THEN
                IF OLD.deleted_at IS NULL AND NEW.deleted_at IS NOT NULL THEN
                    UPDATE entity_active_counts
                    SET active_total = active_total - 1, updated_at = CURRENT_TIMESTAMP
                    WHERE entity_name = 'tests';
                ELSIF OLD.deleted_at IS NOT NULL AND NEW.deleted_at IS NULL THEN
                    UPDATE entity_active_counts
                    SET active_total = active_total + 1, updated_at = CURRENT_TIMESTAMP
                    WHERE entity_name = 'tests';
                END IF;
                RETURN NEW;
            ELSIF TG_OP = 'DELETE' THEN
                IF OLD.deleted_at IS NULL THEN
                    UPDATE entity_active_counts
                    SET active_total = active_total - 1, updated_at = CURRENT_TIMESTAMP
                    WHERE entity_name = 'tests';
                END IF;
                RETURN OLD;
            END IF;
            RETURN NULL;
        END;
        $$;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION sync_tests_active_total_truncate()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $$
        BEGIN
            UPDATE entity_active_counts
            SET active_total = 0, updated_at = CURRENT_TIMESTAMP
            WHERE entity_name = 'tests';
            RETURN NULL;
        END;
        $$;
        """
    )

    op.execute("DROP TRIGGER IF EXISTS tests_active_total_row_trigger ON tests")
    op.execute(
        """
        CREATE TRIGGER tests_active_total_row_trigger
        AFTER INSERT OR UPDATE OF deleted_at OR DELETE ON tests
        FOR EACH ROW
        EXECUTE FUNCTION sync_tests_active_total_row()
        """
    )

    op.execute("DROP TRIGGER IF EXISTS tests_active_total_truncate_trigger ON tests")
    op.execute(
        """
        CREATE TRIGGER tests_active_total_truncate_trigger
        AFTER TRUNCATE ON tests
        FOR EACH STATEMENT
        EXECUTE FUNCTION sync_tests_active_total_truncate()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS tests_active_total_truncate_trigger ON tests")
    op.execute("DROP TRIGGER IF EXISTS tests_active_total_row_trigger ON tests")
    op.execute("DROP FUNCTION IF EXISTS sync_tests_active_total_truncate()")
    op.execute("DROP FUNCTION IF EXISTS sync_tests_active_total_row()")
    op.execute("DELETE FROM entity_active_counts WHERE entity_name = 'tests'")
