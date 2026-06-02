"""notifications

Revision ID: 20260602_0012
Revises: 20260602_0011
Create Date: 2026-06-02 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260602_0012"
down_revision = "20260602_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id UUID PRIMARY KEY DEFAULT uuidv7(),
            kind TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id UUID NOT NULL,
            source_event_type TEXT NOT NULL,
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            target_user_id UUID NULL REFERENCES users(id),
            target_role_key TEXT NULL,
            read_at TIMESTAMPTZ NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS notifications_notifications_created_at
        ON notifications (created_at);
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS notifications_notifications_read_at
        ON notifications (read_at);
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS notifications_notifications_target_user_id
        ON notifications (target_user_id);
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS notifications_notifications_target_role_key
        ON notifications (target_role_key);
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS notifications_notifications_entity
        ON notifications (entity_type, entity_id);
        """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS notifications;")
