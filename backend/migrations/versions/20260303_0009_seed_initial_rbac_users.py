"""seed initial users and role permission matrix (moved to scripts/seed_test_data.py)

This migration used to insert the role definitions, permission catalog,
role/permission matrix and 8 named user accounts. All of that is now owned by
``backend/scripts/seed_test_data.py`` (see ``_seed_bootstrap_data``), which is
the sole seed source for local/dev/test databases — run it once after
``alembic upgrade head``. This migration is kept as a no-op purely to
preserve the revision chain.

Revision ID: 20260303_0009
Revises: 20260303_0008
Create Date: 2026-03-03 00:00:00.000000
"""

# revision identifiers, used by Alembic.
revision = "20260303_0009"
down_revision = "20260303_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
