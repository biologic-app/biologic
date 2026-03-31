"""rbac scope and permissions model

Revision ID: 20260303_0007
Revises: 20260223_0006
Create Date: 2026-03-03 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260303_0007"
down_revision = "20260223_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'role_scope_type') THEN
                CREATE TYPE role_scope_type AS ENUM (
                    'global',
                    'own_branch',
                    'own_lab',
                    'own_objects'
                );
            END IF;
        END
        $$;
        """)

    op.execute("""
        ALTER TABLE roles
        ADD COLUMN IF NOT EXISTS scope_type role_scope_type;
        """)

    op.execute("""
        UPDATE roles
        SET scope_type = CASE
            WHEN key = 'admin' THEN 'global'::role_scope_type
            WHEN key IN ('registrar', 'branch_chief', 'branch_head') THEN 'own_branch'::role_scope_type
            WHEN key IN ('lab_chief', 'lab_head', 'lab_doctor', 'doctor', 'laborant') THEN 'own_lab'::role_scope_type
            WHEN key IN ('sanitary_inspector', 'sanitary_doctor') THEN 'own_objects'::role_scope_type
            ELSE 'global'::role_scope_type
        END
        WHERE scope_type IS NULL;
        """)

    op.execute("""
        UPDATE roles
        SET key = 'lab_chief',
            name = 'Laboratory Chief'
        WHERE key = 'lab_head'
          AND NOT EXISTS (
              SELECT 1
              FROM roles r2
              WHERE r2.key = 'lab_chief'
          );
        """)

    op.execute("""
        UPDATE roles
        SET key = 'branch_chief',
            name = 'Branch Chief'
        WHERE key = 'branch_head'
          AND NOT EXISTS (
              SELECT 1
              FROM roles r2
              WHERE r2.key = 'branch_chief'
          );
        """)

    op.execute("""
        UPDATE roles
        SET key = 'sanitary_inspector',
            name = 'Sanitary Inspector'
        WHERE key = 'sanitary_doctor'
          AND NOT EXISTS (
              SELECT 1
              FROM roles r2
              WHERE r2.key = 'sanitary_inspector'
          );
        """)

    op.execute("""
        INSERT INTO roles (key, name, scope_type)
        VALUES
            ('admin', 'Administrator', 'global'),
            ('registrar', 'Registrar', 'own_branch'),
            ('branch_chief', 'Branch Chief', 'own_branch'),
            ('lab_chief', 'Laboratory Chief', 'own_lab'),
            ('lab_doctor', 'Laboratory Doctor', 'own_lab'),
            ('laborant', 'Laborant', 'own_lab'),
            ('sanitary_inspector', 'Sanitary Inspector', 'own_objects')
        ON CONFLICT (key) DO UPDATE
        SET
            name = EXCLUDED.name,
            scope_type = EXCLUDED.scope_type,
            updated_at = CURRENT_TIMESTAMP;
        """)

    op.execute("""
        ALTER TABLE roles
        ALTER COLUMN scope_type SET DEFAULT 'global'::role_scope_type;
        """)

    op.execute("""
        ALTER TABLE roles
        ALTER COLUMN scope_type SET NOT NULL;
        """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS roles_roles_scope_type
        ON roles (scope_type);
        """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS permissions (
            id UUID PRIMARY KEY DEFAULT uuidv7(),
            resource TEXT NOT NULL,
            action TEXT NOT NULL
        );
        """)

    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS permissions_permissions_resource_action
        ON permissions (resource, action);
        """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS user_scopes (
            id UUID PRIMARY KEY DEFAULT uuidv7(),
            user_id UUID NOT NULL REFERENCES users(id),
            scope_id UUID NULL
        );
        """)

    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS user_scopes_user_scopes_user_id_scope_id
        ON user_scopes (user_id, scope_id);
        """)

    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS user_scopes_user_scopes_user_id_null_scope_id
        ON user_scopes (user_id)
        WHERE scope_id IS NULL;
        """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS user_scopes_user_scopes_scope_id
        ON user_scopes (scope_id);
        """)

    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'role_permissions'
                  AND column_name = 'resource'
            ) THEN
                ALTER TABLE role_permissions RENAME TO role_permissions_legacy;

                CREATE TABLE role_permissions (
                    id UUID PRIMARY KEY DEFAULT uuidv7(),
                    role_id UUID NOT NULL REFERENCES roles(id),
                    permission_id UUID NOT NULL REFERENCES permissions(id)
                );

                CREATE UNIQUE INDEX role_permissions_role_permissions_role_id_permission_id
                ON role_permissions (role_id, permission_id);

                INSERT INTO permissions (resource, action)
                SELECT DISTINCT resource, action
                FROM role_permissions_legacy
                ON CONFLICT (resource, action) DO NOTHING;

                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'role_permissions_legacy'
                      AND column_name = 'deleted_at'
                ) THEN
                    INSERT INTO role_permissions (role_id, permission_id)
                    SELECT DISTINCT rp.role_id, p.id
                    FROM role_permissions_legacy rp
                    JOIN permissions p
                      ON p.resource = rp.resource
                     AND p.action = rp.action
                    WHERE rp.deleted_at IS NULL
                    ON CONFLICT (role_id, permission_id) DO NOTHING;
                ELSE
                    INSERT INTO role_permissions (role_id, permission_id)
                    SELECT DISTINCT rp.role_id, p.id
                    FROM role_permissions_legacy rp
                    JOIN permissions p
                      ON p.resource = rp.resource
                     AND p.action = rp.action
                    ON CONFLICT (role_id, permission_id) DO NOTHING;
                END IF;

                DROP TABLE role_permissions_legacy;
            END IF;
        END
        $$;
        """)

    op.execute("""
        DROP TABLE IF EXISTS user_roles;
        """)


def downgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id UUID NOT NULL REFERENCES users(id),
            role_id UUID NOT NULL REFERENCES roles(id),
            UNIQUE (user_id, role_id)
        );
        """)

    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'role_permissions'
                  AND column_name = 'permission_id'
            ) THEN
                ALTER TABLE role_permissions RENAME TO role_permissions_new;

                CREATE TABLE role_permissions (
                    role_id UUID NOT NULL REFERENCES roles(id),
                    resource TEXT NOT NULL,
                    action TEXT NOT NULL
                );

                CREATE UNIQUE INDEX role_permissions_role_permissions_role_id_resource_action
                ON role_permissions (role_id, resource, action);

                INSERT INTO role_permissions (role_id, resource, action)
                SELECT DISTINCT rp.role_id, p.resource, p.action
                FROM role_permissions_new rp
                JOIN permissions p ON p.id = rp.permission_id;

                DROP TABLE role_permissions_new;
            END IF;
        END
        $$;
        """)

    op.execute("""
        DROP TABLE IF EXISTS user_scopes;
        """)

    op.execute("""
        DROP TABLE IF EXISTS permissions;
        """)

    op.execute("""
        DROP INDEX IF EXISTS roles_roles_scope_type;
        """)

    op.execute("""
        ALTER TABLE roles
        DROP COLUMN IF EXISTS scope_type;
        """)

    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'role_scope_type') THEN
                DROP TYPE role_scope_type;
            END IF;
        END
        $$;
        """)
