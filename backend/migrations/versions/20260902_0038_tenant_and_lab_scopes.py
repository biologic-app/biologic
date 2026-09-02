"""add direct tenant and laboratory scopes to operational tables

Revision ID: 20260902_0038
Revises: 20260902_0037
Create Date: 2026-09-02 00:00:00.000000
"""

from alembic import op

revision = "20260902_0038"
down_revision = "20260902_0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Scope columns intentionally have no foreign keys. Scope ownership is
    # validated by the application and can refer to an external tenant source.
    for table, column in (
        ("directions", "branch_id"),
        ("samples", "branch_id"),
        ("research", "branch_id"),
        ("tests", "branch_id"),
        ("protocols", "branch_id"),
        ("doctors", "lab_id"),
        ("indicators", "lab_id"),
    ):
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} uuid")
        op.execute(f"CREATE INDEX IF NOT EXISTS {table}_{column}_idx ON {table} ({column})")


def downgrade() -> None:
    for table, column in (
        ("directions", "branch_id"),
        ("samples", "branch_id"),
        ("research", "branch_id"),
        ("tests", "branch_id"),
        ("protocols", "branch_id"),
        ("doctors", "lab_id"),
        ("indicators", "lab_id"),
    ):
        op.execute(f"DROP INDEX IF EXISTS {table}_{column}_idx")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {column}")
