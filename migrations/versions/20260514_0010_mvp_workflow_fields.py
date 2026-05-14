"""add mvp workflow fields

Revision ID: 20260514_0010
Revises: 20260303_0009
Create Date: 2026-05-14 00:10:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260514_0010"
down_revision: str | None = "20260303_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE directions
          ADD COLUMN IF NOT EXISTS import_warnings jsonb
        """
    )
    op.execute(
        """
        ALTER TABLE samples
          ADD COLUMN IF NOT EXISTS deadline timestamptz,
          ADD COLUMN IF NOT EXISTS verdict text
        """
    )
    op.execute(
        """
        ALTER TABLE research
          ADD COLUMN IF NOT EXISTS lab_id uuid
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname = 'fk_research_lab_id_labs_id'
              AND conrelid = 'research'::regclass
          ) THEN
            ALTER TABLE research
              ADD CONSTRAINT fk_research_lab_id_labs_id
              FOREIGN KEY (lab_id) REFERENCES labs(id);
          END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE research DROP CONSTRAINT IF EXISTS fk_research_lab_id_labs_id")
    op.execute("ALTER TABLE research DROP COLUMN IF EXISTS lab_id")
    op.execute("ALTER TABLE samples DROP COLUMN IF EXISTS verdict")
    op.execute("ALTER TABLE samples DROP COLUMN IF EXISTS deadline")
    op.execute("ALTER TABLE directions DROP COLUMN IF EXISTS import_warnings")
