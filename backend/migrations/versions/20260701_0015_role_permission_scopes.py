"""bind role_permission scopes to role scope_type

Revision ID: 20260701_0015
Revises: 20260608_0014
Create Date: 2026-07-01 00:00:00.000000
"""

from alembic import op

revision = "20260701_0015"
down_revision = "20260608_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE role_permissions rp
        SET scope = CASE r.scope_type
            WHEN 'global'      THEN 'all'::access_scope_type
            WHEN 'own_branch'  THEN 'own_branch'::access_scope_type
            WHEN 'own_lab'     THEN 'own_lab'::access_scope_type
            WHEN 'own_objects' THEN 'own'::access_scope_type
            ELSE 'all'::access_scope_type
        END
        FROM roles r
        WHERE rp.role_id = r.id;
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE role_permissions
        SET scope = 'all'::access_scope_type;
    """)
