"""simplify research and test statuses

Collapse the research/test lifecycle to a single entry state:

    research: draft/ordered -> in_progress
    tests:    queued        -> in_progress

Existing rows are migrated onto ``in_progress`` and the now-unused status
dictionary rows (research ``draft``/``ordered``, test ``queued``) are removed.

Revision ID: 20260719_0029
Revises: 20260714_0028
Create Date: 2026-07-19 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260719_0029"
down_revision = "20260714_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Migrate operational rows onto the surviving in_progress state first, so
    #    no research/test references a status row that is about to be removed.
    op.execute(
        """
        UPDATE research
        SET status_id = (
            SELECT id FROM research_statuses WHERE code = 'in_progress' LIMIT 1
        )
        WHERE status_id IN (
            SELECT id FROM research_statuses WHERE code IN ('draft', 'ordered')
        )
        """
    )
    op.execute(
        """
        UPDATE tests
        SET status_id = (
            SELECT id FROM test_statuses WHERE code = 'in_progress' LIMIT 1
        )
        WHERE status_id IN (
            SELECT id FROM test_statuses WHERE code = 'queued'
        )
        """
    )

    # 2. Remove the now-unused status dictionary rows. Status seed migrations
    #    insert plain rows (no soft-delete convention on these dictionaries), so
    #    a hard delete is the right inverse — and it is safe now that nothing
    #    references them.
    op.execute("DELETE FROM research_statuses WHERE code IN ('draft', 'ordered')")
    op.execute("DELETE FROM test_statuses WHERE code = 'queued'")


def downgrade() -> None:
    # Best-effort restore of the removed dictionary rows. Operational rows are
    # not moved back (the original draft/ordered/queued assignment is lost).
    op.execute(
        """
        INSERT INTO research_statuses (code, name)
        VALUES
            ('draft', 'Черновик'),
            ('ordered', 'Запланировано')
        ON CONFLICT (code) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO test_statuses (code, name)
        VALUES ('queued', 'Запланировано')
        ON CONFLICT (code) DO NOTHING
        """
    )
