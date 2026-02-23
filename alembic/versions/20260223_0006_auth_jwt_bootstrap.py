"""add auth bootstrap data and refresh token version

Revision ID: 20260223_0006
Revises: 20260219_0005
Create Date: 2026-02-23 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260223_0006"
down_revision = "20260219_0005"
branch_labels = None
depends_on = None

_ADMIN_PASSWORD_HASH = "$2b$12$CpbnQTvZQC2uOGw7iittjeyMn4A3hWeNm4JTXPwd17s3LsLsAJ3iW"


def upgrade() -> None:
    op.execute("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS refresh_token_version INTEGER NOT NULL DEFAULT 0
        """)

    op.execute("""
        INSERT INTO roles (key, name)
        VALUES ('admin', 'Administrator')
        ON CONFLICT (key) DO UPDATE
        SET
            name = EXCLUDED.name,
            updated_at = CURRENT_TIMESTAMP
        """)

    op.execute(f"""
        WITH admin_role AS (
            SELECT id
            FROM roles
            WHERE key = 'admin'
            LIMIT 1
        )
        INSERT INTO users (
            username,
            password_hash,
            refresh_token_version,
            code,
            first_name,
            last_name,
            patronymic,
            is_registrar,
            is_lab_head,
            is_branch_head,
            role_id,
            lab_id
        )
        SELECT
            'admin',
            '{_ADMIN_PASSWORD_HASH}',
            0,
            'ADM-001',
            'System',
            'Administrator',
            NULL,
            false,
            false,
            false,
            admin_role.id,
            NULL
        FROM admin_role
        ON CONFLICT (username) DO UPDATE
        SET
            password_hash = EXCLUDED.password_hash,
            refresh_token_version = 0,
            code = EXCLUDED.code,
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            patronymic = EXCLUDED.patronymic,
            is_registrar = EXCLUDED.is_registrar,
            is_lab_head = EXCLUDED.is_lab_head,
            is_branch_head = EXCLUDED.is_branch_head,
            role_id = EXCLUDED.role_id,
            lab_id = EXCLUDED.lab_id,
            updated_at = CURRENT_TIMESTAMP
        """)

    op.execute("""
        INSERT INTO user_roles (user_id, role_id)
        SELECT u.id, u.role_id
        FROM users u
        WHERE u.username = 'admin'
        ON CONFLICT (user_id, role_id) DO NOTHING
        """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM user_roles ur
        USING users u
        WHERE ur.user_id = u.id
          AND u.username = 'admin'
          AND u.code = 'ADM-001'
        """)

    op.execute("""
        DELETE FROM users
        WHERE username = 'admin'
          AND code = 'ADM-001'
        """)

    op.execute("""
        ALTER TABLE users
        DROP COLUMN IF EXISTS refresh_token_version
        """)
