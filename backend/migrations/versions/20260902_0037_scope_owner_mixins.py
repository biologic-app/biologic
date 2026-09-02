"""add owner scope and remove implicit scope foreign keys

Revision ID: 20260902_0037
Revises: 20260828_0036
Create Date: 2026-09-02 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "20260902_0037"
down_revision = "20260828_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "directions",
        sa.Column("owner_id", sa.UUID(), nullable=True),
    )
    op.create_index("directions_directions_owner_id", "directions", ["owner_id"])

    for table, constraint in (
        ("labs", "fk_labs_branch_id_branches_id"),
        ("objects", "fk_objects_branch_id_branches_id"),
        ("change_log", "fk_change_log_branch_id_branches_id"),
        ("role_subscription_rules", "fk_role_subscription_rules_branch_id_branches_id"),
        ("role_subscription_rules", "fk_role_subscription_rules_lab_id_labs_id"),
        ("users", "fk_users_lab_id_labs_id"),
        ("research_goals", "fk_research_goals_lab_id_labs_id"),
        ("research", "fk_research_lab_id_labs_id"),
        ("sample_labs", "fk_sample_labs_lab_id_labs_id"),
    ):
        op.execute(f'ALTER TABLE {table} DROP CONSTRAINT IF EXISTS "{constraint}"')


def downgrade() -> None:
    op.drop_index("directions_directions_owner_id", table_name="directions")
    op.drop_column("directions", "owner_id")
