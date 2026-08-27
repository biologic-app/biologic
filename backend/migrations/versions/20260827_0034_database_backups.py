"""Registry of full-database dumps stored on the filesystem."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260827_0034"
down_revision = "20260827_0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "database_backups",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuidv7()"),
            nullable=False,
        ),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("format", sa.Text(), nullable=False),
        sa.Column("origin", sa.Text(), server_default=sa.text("'export'"), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'in_progress'"), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("restored_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_database_backups"),
    )
    op.create_index("ix_database_backups_created_at", "database_backups", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_database_backups_created_at", table_name="database_backups")
    op.drop_table("database_backups")
