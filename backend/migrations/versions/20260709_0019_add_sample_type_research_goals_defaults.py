"""add sample_type_research_goals defaults

Revision ID: 20260709_0019
Revises: 20260709_0018
Create Date: 2026-07-09 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260709_0019"
down_revision = "20260709_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Default research goals suggested per sample type. Starts empty; populated
    # through the admin CRUD endpoints. The (sample_type_id, research_goal_id)
    # pair is unique only among live rows so a default can be removed (soft
    # delete) and re-added later.
    op.execute("""
        CREATE TABLE IF NOT EXISTS sample_type_research_goals (
            id UUID PRIMARY KEY DEFAULT uuidv7(),
            sample_type_id UUID NOT NULL
                REFERENCES sample_types (id) ON DELETE CASCADE,
            research_goal_id UUID NOT NULL
                REFERENCES research_goals (id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMPTZ NULL
        );
        """)

    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS sample_type_research_goals_unique_pair
        ON sample_type_research_goals (sample_type_id, research_goal_id)
        WHERE deleted_at IS NULL;
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS sample_type_research_goals_sample_type_id
        ON sample_type_research_goals (sample_type_id);
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS sample_type_research_goals_research_goal_id
        ON sample_type_research_goals (research_goal_id);
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS sample_type_research_goals_deleted_at
        ON sample_type_research_goals (deleted_at);
        """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS sample_type_research_goals;")
