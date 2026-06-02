"""access permission scopes and user overrides

Revision ID: 20260602_0011
Revises: 20260514_0010
Create Date: 2026-06-02 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260602_0011"
down_revision = "20260514_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'access_scope_type') THEN
                CREATE TYPE access_scope_type AS ENUM (
                    'own',
                    'own_lab',
                    'all_labs',
                    'own_branch',
                    'all_branches',
                    'all'
                );
            END IF;
        END
        $$;
        """)

    op.execute("""
        ALTER TABLE role_permissions
        ADD COLUMN IF NOT EXISTS scope access_scope_type;
        """)

    op.execute("""
        UPDATE role_permissions
        SET scope = 'all'::access_scope_type
        WHERE scope IS NULL;
        """)

    op.execute("""
        ALTER TABLE role_permissions
        ALTER COLUMN scope SET DEFAULT 'all'::access_scope_type;
        """)

    op.execute("""
        ALTER TABLE role_permissions
        ALTER COLUMN scope SET NOT NULL;
        """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS user_permission_overrides (
            id UUID PRIMARY KEY DEFAULT uuidv7(),
            user_id UUID NOT NULL REFERENCES users(id),
            permission_id UUID NOT NULL REFERENCES permissions(id),
            allowed BOOLEAN NOT NULL,
            scope access_scope_type NULL
        );
        """)

    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS user_permission_overrides_user_id_permission_id
        ON user_permission_overrides (user_id, permission_id);
        """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS user_permission_overrides_permission_id
        ON user_permission_overrides (permission_id);
        """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS user_permission_overrides;
        """)

    op.execute("""
        ALTER TABLE role_permissions
        DROP COLUMN IF EXISTS scope;
        """)

    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'access_scope_type') THEN
                DROP TYPE access_scope_type;
            END IF;
        END
        $$;
        """)
