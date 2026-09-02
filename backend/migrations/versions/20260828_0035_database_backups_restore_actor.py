"""Track who restored a dump, and whether that restore succeeded."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260828_0035"
down_revision = "20260827_0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "database_backups",
        sa.Column("restored_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "database_backups",
        sa.Column("restore_status", sa.Text(), nullable=True),
    )
    op.add_column(
        "database_backups",
        sa.Column("restore_error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("database_backups", "restore_error")
    op.drop_column("database_backups", "restore_status")
    op.drop_column("database_backups", "restored_by")
