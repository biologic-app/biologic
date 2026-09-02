"""add tenant branch_id to every application table except branches

Revision ID: 20260902_0039
Revises: 20260902_0038
Create Date: 2026-09-02 00:00:00.000000
"""

from alembic import op

revision = "20260902_0039"
down_revision = "20260902_0038"
branch_labels = None
depends_on = None


TABLES = (
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
    "research",
    "research_goals",
    "research_statuses",
    "roles",
    "role_permissions",
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
    "user_scopes",
    "users",
    "workflow_attachments",
    "workflow_run_events",
    "workflow_schema_versions",
    "workflow_step_executions",
    "workflow_templates",
    "workflow_runs",
)


def upgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS branch_id uuid")
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {table}_branch_id_idx ON {table} (branch_id)"
        )

    op.execute("ALTER TABLE samples ADD COLUMN IF NOT EXISTS owner_id uuid")
    op.execute("CREATE INDEX IF NOT EXISTS samples_owner_id_idx ON samples (owner_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS samples_owner_id_idx")
    op.execute("ALTER TABLE samples DROP COLUMN IF EXISTS owner_id")
    for table in reversed(TABLES):
        op.execute(f"DROP INDEX IF EXISTS {table}_branch_id_idx")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS branch_id")
