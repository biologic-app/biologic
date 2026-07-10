"""role subscription rules: optional status filter

Extends role_subscription_rules with an optional status_code so a rule can be
narrowed to a specific lifecycle status of the entity (e.g. "lab chiefs follow
only rejected samples"), on top of the existing branch/lab scoping. NULL means
"any status" — the previous, unfiltered behaviour. Stored as the stable code
string (see src/core/status_codes.py), not a status row id, because a single
column has to reference either direction_statuses or sample_statuses depending
on entity_type — the code taxonomy is the shared, stable key across both.

Revision ID: 20260712_0026
Revises: 20260711_0025
Create Date: 2026-07-12 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260712_0026"
down_revision = "20260711_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE role_subscription_rules
        ADD COLUMN IF NOT EXISTS status_code TEXT;
        """)
    op.execute("""
        ALTER TABLE role_subscription_rules
        DROP CONSTRAINT IF EXISTS role_subscription_rules_status_code_check;
        """)
    op.execute("""
        ALTER TABLE role_subscription_rules
        ADD CONSTRAINT role_subscription_rules_status_code_check CHECK (
            status_code IS NULL
            OR (
                entity_type = 'directions'
                AND status_code IN (
                    'draft', 'registered', 'in_progress', 'partially_completed', 'completed'
                )
            )
            OR (
                entity_type = 'samples'
                AND status_code IN (
                    'pending', 'registered', 'in_progress', 'analyzed', 'completed', 'rejected'
                )
            )
        );
        """)
    op.execute("DROP INDEX IF EXISTS role_subscription_rules_unique_rule;")
    op.execute("""
        CREATE UNIQUE INDEX role_subscription_rules_unique_rule
        ON role_subscription_rules (
            role_id,
            entity_type,
            COALESCE(branch_id, '00000000-0000-0000-0000-000000000000'),
            COALESCE(lab_id, '00000000-0000-0000-0000-000000000000'),
            COALESCE(status_code, '')
        )
        WHERE deleted_at IS NULL;
        """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS role_subscription_rules_unique_rule;")
    op.execute("""
        CREATE UNIQUE INDEX role_subscription_rules_unique_rule
        ON role_subscription_rules (
            role_id,
            entity_type,
            COALESCE(branch_id, '00000000-0000-0000-0000-000000000000'),
            COALESCE(lab_id, '00000000-0000-0000-0000-000000000000')
        )
        WHERE deleted_at IS NULL;
        """)
    op.execute("""
        ALTER TABLE role_subscription_rules
        DROP CONSTRAINT IF EXISTS role_subscription_rules_status_code_check;
        """)
    op.execute("ALTER TABLE role_subscription_rules DROP COLUMN IF EXISTS status_code;")
