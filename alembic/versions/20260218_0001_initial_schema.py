"""initial schema

Revision ID: 20260218_0001
Revises:
Create Date: 2026-02-18 00:00:00.000000
"""

from alembic import op

from src.models import Base

# revision identifiers, used by Alembic.
revision = "20260218_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL 15 doesn't provide uuidv7() out of the box.
    # Keep the domain contract (`DEFAULT uuidv7()`) with a compatibility function.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
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

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
    op.execute("DROP FUNCTION IF EXISTS uuidv7()")
