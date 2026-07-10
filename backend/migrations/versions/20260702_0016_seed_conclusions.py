"""seed typical conclusions (moved to scripts/seed_test_data.py)

This migration used to insert 5 typical conclusion rows. That is now owned by
``backend/scripts/seed_test_data.py`` (see ``_seed_bootstrap_data``), which is
the sole seed source for local/dev/test databases — run it once after
``alembic upgrade head``. This migration is kept as a no-op purely to
preserve the revision chain.

Revision ID: 20260702_0016
Revises: 20260701_0015
Create Date: 2026-07-02 00:00:00.000000
"""

# revision identifiers, used by Alembic.
revision = "20260702_0016"
down_revision = "20260701_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
