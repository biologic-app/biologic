"""add color to status tables

Revision ID: 20260714_0029
Revises: 20260719_0029
Create Date: 2026-07-14 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260714_0029"
down_revision = "20260719_0029"
branch_labels = None
depends_on = None

# (table, {code: color}) — literals inlined so the migration stays frozen and
# self-contained (do NOT import src.core.status_colors here).
_STATUS_COLORS: tuple[tuple[str, dict[str, str]], ...] = (
    (
        "direction_statuses",
        {
            "draft": "gray",
            "registered": "indigo",
            "in_progress": "blue",
            "partially_completed": "lime",
            "completed": "green",
        },
    ),
    (
        "sample_statuses",
        {
            "pending": "amber",
            "registered": "indigo",
            "in_progress": "blue",
            "analyzed": "violet",
            "completed": "green",
            "rejected": "red",
        },
    ),
    (
        "research_statuses",
        {
            "in_progress": "blue",
            "completed": "green",
            "rejected": "red",
        },
    ),
    (
        "test_statuses",
        {
            "in_progress": "blue",
            "completed": "green",
            "rejected": "red",
        },
    ),
)


def upgrade() -> None:
    for table, colors in _STATUS_COLORS:
        op.add_column(table, sa.Column("color", sa.Text(), nullable=True))
        for code, color in colors.items():
            op.execute(
                sa.text(
                    f"UPDATE {table} SET color = :color WHERE code = :code"  # noqa: S608
                ).bindparams(color=color, code=code)
            )


def downgrade() -> None:
    for table, _ in _STATUS_COLORS:
        op.drop_column(table, "color")
