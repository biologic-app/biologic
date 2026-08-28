"""bind JWTs to revocable sessions and normalize RBAC system role."""
# SQL statements are intentionally kept readable as one operation per line.
# ruff: noqa: E501
from alembic import op

revision = "20260827_0032"
down_revision = "1f0437173350"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Keep the legacy column during the rolling upgrade; application code reads
    # ``token_version`` while older workers may still write the old name.
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active'")
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='refresh_token_version')
               AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='token_version') THEN
                UPDATE users SET token_version = refresh_token_version
                WHERE token_version = 0 AND refresh_token_version <> 0;
            END IF;
        END $$;
    """)
    op.execute("ALTER TABLE roles ADD COLUMN IF NOT EXISTS is_system BOOLEAN NOT NULL DEFAULT FALSE")
    op.execute("UPDATE roles SET key = 'superadmin', name = 'Superadmin', is_system = TRUE WHERE key = 'developer'")
    op.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id UUID PRIMARY KEY DEFAULT uuidv7(), user_id UUID NOT NULL REFERENCES users(id),
            expires_at TIMESTAMPTZ NOT NULL, revoked_at TIMESTAMPTZ,
            token_version INTEGER NOT NULL DEFAULT 0,
            last_seen_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS sessions_user_id ON sessions(user_id)")
    op.execute("ALTER TABLE user_scopes ADD COLUMN IF NOT EXISTS scope_kind TEXT NOT NULL DEFAULT 'object'")
    op.execute("""
        UPDATE user_scopes us
        SET scope_kind = CASE r.scope_type::text
            WHEN 'own_branch' THEN 'branch'
            WHEN 'own_lab' THEN 'lab'
            ELSE 'object'
        END
        FROM users u JOIN roles r ON r.id = u.role_id
        WHERE us.user_id = u.id AND (us.scope_kind IS NULL OR us.scope_kind = 'object')
    """)
    op.execute("ALTER TABLE user_scopes ADD CONSTRAINT user_scopes_scope_kind_check CHECK (scope_kind IN ('branch','lab','object'))")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS sessions")
    op.execute("ALTER TABLE user_scopes DROP CONSTRAINT IF EXISTS user_scopes_scope_kind_check")
    op.execute("ALTER TABLE roles DROP COLUMN IF EXISTS is_system")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS status")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS token_version")
    # ``refresh_token_version`` remains for compatibility with pre-migration
    # clients and is removed in a later cleanup migration.
    op.execute("ALTER TABLE user_scopes DROP COLUMN IF EXISTS scope_kind")
