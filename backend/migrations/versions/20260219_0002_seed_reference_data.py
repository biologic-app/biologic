"""seed reference data (moved to scripts/seed_test_data.py)

This migration used to insert reference rows directly (roles, status tables,
~100 synthetic sample_types/protocol_types/branches/labs/objects/doctors/
research_goals/indicators, a permissions/role_permissions matrix, and ~100
placeholder users). All of that is now owned by
``backend/scripts/seed_test_data.py`` (see ``_seed_bootstrap_data`` and
``_seed_reference_rows``), which is the sole seed source for local/dev/test
databases — run it once after ``alembic upgrade head``. This migration is
kept as a no-op purely to preserve the revision chain.

Revision ID: 20260219_0002
Revises: 20260218_0001
Create Date: 2026-02-19 00:00:00.000000
"""

# revision identifiers, used by Alembic.
revision = "20260219_0002"
down_revision = "20260218_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
