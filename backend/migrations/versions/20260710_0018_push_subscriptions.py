"""push_subscriptions

Revision ID: 20260710_0018
Revises: 20260703_0017
Create Date: 2026-07-10 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260710_0018"
down_revision = "20260703_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id UUID PRIMARY KEY DEFAULT uuidv7(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            endpoint TEXT NOT NULL,
            p256dh TEXT NOT NULL,
            auth TEXT NOT NULL,
            user_agent TEXT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_push_subscriptions_endpoint UNIQUE (endpoint)
        );
        """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS push_subscriptions_user_id
        ON push_subscriptions (user_id);
        """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS push_subscriptions;")
