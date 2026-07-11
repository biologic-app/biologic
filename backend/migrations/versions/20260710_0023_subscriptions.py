"""user subscriptions to directions and samples

A user can follow a direction or a sample to receive its notifications.
Explicit rows live here; implicit followers (registrars follow everything,
the direction owner follows their own entities) are derived at read time
and never stored. The (user_id, entity_type, entity_id) triple is unique
only among live rows so a subscription can be soft-deleted and re-added.

Revision ID: 20260710_0023
Revises: 20260709_0022
Create Date: 2026-07-10 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260710_0023"
down_revision = "20260709_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id UUID PRIMARY KEY DEFAULT uuidv7(),
            user_id UUID NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id UUID NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMPTZ NULL,
            CONSTRAINT fk_subscriptions_user_id_users_id
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            CONSTRAINT subscriptions_entity_type_check
                CHECK (entity_type IN ('directions', 'samples'))
        );
        """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS subscriptions_unique_triple
        ON subscriptions (user_id, entity_type, entity_id)
        WHERE deleted_at IS NULL;
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS subscriptions_entity
        ON subscriptions (entity_type, entity_id);
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS subscriptions_subscriptions_deleted_at
        ON subscriptions (deleted_at);
        """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS subscriptions;")
