"""Make the current auth model compatible with the existing local database."""

from alembic import op

revision = "20260827_0033"
down_revision = "2e61aabeeb93"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The local database was migrated by the newer RBAC branch and has
    # ``token_version``. This branch still reads ``refresh_token_version``.
    # Keep both columns during the compatibility window and preserve values.
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS refresh_token_version "
        "INTEGER NOT NULL DEFAULT 0"
    )
    op.execute(
        "UPDATE users SET refresh_token_version = token_version "
        "WHERE refresh_token_version = 0 AND token_version IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS refresh_token_version")
