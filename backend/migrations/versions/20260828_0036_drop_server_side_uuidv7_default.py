"""Drop server-side uuidv7 default; ids are generated in Python now.

Revision ID: 20260828_0036
Revises: 20260828_0035
Create Date: 2026-08-28 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "20260828_0036"
down_revision = "20260828_0035"
branch_labels = None
depends_on = None

TABLES = (
    "branches",
    "change_log",
    "conclusions",
    "database_backups",
    "directions",
    "direction_statuses",
    "doctors",
    "indicators",
    "labs",
    "notifications",
    "objects",
    "permissions",
    "protocols",
    "protocol_types",
    "research_goals",
    "research",
    "research_statuses",
    "role_permissions",
    "roles",
    "role_subscription_rules",
    "sample_labs",
    "samples",
    "sample_statuses",
    "sample_types",
    "sessions",
    "subscriptions",
    "tests",
    "test_statuses",
    "ui_events",
    "user_permission_overrides",
    "users",
    "user_scopes",
    "workflow_attachments",
    "workflow_run_events",
    "workflow_runs",
    "workflow_schema_versions",
    "workflow_step_executions",
    "workflow_templates",
)


def upgrade() -> None:
    for table in TABLES:
        op.alter_column(table, "id", server_default=None)
    op.execute("DROP FUNCTION IF EXISTS public.uuidv7()")


def downgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION uuidv7()
        RETURNS uuid
        LANGUAGE SQL
        AS $$
            SELECT gen_random_uuid();
        $$;
        """
    )
    for table in TABLES:
        op.alter_column(table, "id", server_default=sa.text("uuidv7()"))
