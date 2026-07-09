"""sample ↔ laboratory assignments (many-to-many)

A sample belongs to one or more laboratories, derived at import time from the
legacy Бак/Т-Х/Т-Б/РВ/ПЦР mark columns. The (sample_id, lab_id) pair is unique
only among live rows so an assignment can be soft-deleted and re-added later.

Revision ID: 20260709_0021
Revises: 20260709_0020
Create Date: 2026-07-09 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260709_0021"
down_revision = "20260709_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS sample_labs (
            id UUID PRIMARY KEY DEFAULT uuidv7(),
            sample_id UUID NOT NULL,
            lab_id UUID NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMPTZ NULL,
            CONSTRAINT fk_sample_labs_sample_id_samples_id
                FOREIGN KEY (sample_id) REFERENCES samples (id) ON DELETE CASCADE,
            CONSTRAINT fk_sample_labs_lab_id_labs_id
                FOREIGN KEY (lab_id) REFERENCES labs (id) ON DELETE CASCADE
        );
        """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS sample_labs_unique_pair
        ON sample_labs (sample_id, lab_id)
        WHERE deleted_at IS NULL;
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS sample_labs_sample_id
        ON sample_labs (sample_id);
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS sample_labs_lab_id
        ON sample_labs (lab_id);
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS sample_labs_deleted_at
        ON sample_labs (deleted_at);
        """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS sample_labs;")
