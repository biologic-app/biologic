from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Index,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.uuid7 import new_uuid7
from src.infrastructure.db.models.base import Base
from src.infrastructure.db.models.mixins import TenantMixin


class ChangeLog(TenantMixin, Base):
    __tablename__ = "change_log"
    __table_args__ = (
        Index("change_log_change_log_entity", "entity_type", "entity_id"),
        Index("change_log_change_log_actor_id", "actor_id"),
        Index("change_log_change_log_branch_id", "branch_id"),
        Index("change_log_change_log_created_at", "created_at"),
        Index("ix_change_log_workflow_run_id", "workflow_run_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=new_uuid7,
    )
    entity_type: Mapped[str | None] = mapped_column(Text)
    entity_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    action: Mapped[str | None] = mapped_column(Text)
    actor_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    actor_name: Mapped[str | None] = mapped_column(Text)
    snapshot: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    diff: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    # Correlates a domain mutation with the workflow run that triggered it
    # (via execute-step); NULL for mutations made outside a workflow run.
    workflow_run_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
