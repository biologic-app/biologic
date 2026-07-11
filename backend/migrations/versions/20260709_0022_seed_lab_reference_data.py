"""seed the 5 real laboratories with research goals and indicators

Moved to scripts/seed_test_data.py. This migration used to insert the 5 real
laboratories (BAK/TH/TB/RV/PCR), a
handful of placeholder research goals per lab and indicators linking them to
the first 5 synthetic reference sample types. All of that is superseded by
the realistic dataset in ``backend/scripts/seed_test_data.py``
(``_seed_reference_rows``: the same 5 labs, 18 real research goals and ~90
indicators), which is the sole seed source for local/dev/test databases — run
it once after ``alembic upgrade head``. This migration is kept as a no-op
purely to preserve the revision chain.

Revision ID: 20260709_0022
Revises: 20260709_0021
Create Date: 2026-07-09 00:00:00.000000
"""

# revision identifiers, used by Alembic.
revision = "20260709_0022"
down_revision = "20260709_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
