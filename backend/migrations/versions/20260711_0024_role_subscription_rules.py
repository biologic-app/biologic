"""role subscription rules and doctor user link

Mandatory, admin-configured subscriptions keyed on a role, optionally scoped to
a branch and/or a lab. Followers are derived at read time (see
SubscriptionCrudRepository) and never stored per-entity. Also adds the
nullable doctors.user_id link so a direction's sanitary doctor implicitly
follows their own directions and samples.

The two rows that preserve today's behaviour (registrars follow every
direction and every sample, globally and unscoped) used to be seeded here;
that is now owned by ``backend/scripts/seed_test_data.py`` (see
``ROLE_SUBSCRIPTION_RULES`` / ``_seed_bootstrap_data``), which is the sole
seed source for local/dev/test databases — run it once after
``alembic upgrade head``.

Revision ID: 20260711_0024
Revises: 20260710_0023
Create Date: 2026-07-11 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260711_0024"
down_revision = "20260710_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS role_subscription_rules (
            id UUID PRIMARY KEY DEFAULT uuidv7(),
            role_id UUID NOT NULL REFERENCES roles (id),
            entity_type TEXT NOT NULL,
            branch_id UUID REFERENCES branches (id),
            lab_id UUID REFERENCES labs (id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMPTZ,
            CONSTRAINT role_subscription_rules_entity_type_check
                CHECK (entity_type IN ('directions', 'samples')),
            CONSTRAINT role_subscription_rules_lab_scope_check
                CHECK (lab_id IS NULL OR entity_type = 'samples')
        );
        """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS role_subscription_rules_unique_rule
        ON role_subscription_rules (
            role_id,
            entity_type,
            COALESCE(branch_id, '00000000-0000-0000-0000-000000000000'),
            COALESCE(lab_id, '00000000-0000-0000-0000-000000000000')
        )
        WHERE deleted_at IS NULL;
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS role_subscription_rules_role_id
        ON role_subscription_rules (role_id);
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS role_subscription_rules_deleted_at
        ON role_subscription_rules (deleted_at);
        """)

    op.execute("""
        ALTER TABLE doctors
        ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users (id);
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS doctors_doctors_user_id
        ON doctors (user_id);
        """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS doctors_doctors_user_id;")
    op.execute("ALTER TABLE doctors DROP COLUMN IF EXISTS user_id;")
    op.execute("DROP TABLE IF EXISTS role_subscription_rules;")
