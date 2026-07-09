"""add ui_events telemetry table

Revision ID: 20260709_0018
Revises: 20260703_0017
Create Date: 2026-07-09 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260709_0018"
down_revision = "20260703_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Plain table for now. TODO: convert to a native PostgreSQL RANGE
    # partitioned table keyed on `created_at` (e.g. monthly partitions) once
    # event volume warrants it, plus a scheduled job to drop partitions past
    # the retention window (see docstring on `UiEvent`). Anonymous by design:
    # only element/session identifiers are stored, never form values or
    # other user-entered content.
    op.execute("""
        CREATE TABLE IF NOT EXISTS ui_events (
            id UUID PRIMARY KEY DEFAULT uuidv7(),
            event TEXT NOT NULL,
            element_id TEXT NULL,
            route TEXT NOT NULL,
            role TEXT NULL,
            session_id TEXT NOT NULL,
            ts TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ui_events_ui_events_created_at
        ON ui_events (created_at);
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ui_events_ui_events_session_id
        ON ui_events (session_id);
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ui_events_ui_events_event
        ON ui_events (event);
        """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ui_events;")
