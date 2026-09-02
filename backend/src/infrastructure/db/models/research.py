from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.uuid7 import new_uuid7
from src.infrastructure.db.models.base import Base
from src.infrastructure.db.models.mixins import LabMixin, SoftDeleteMixin, TenantMixin


class Research(TenantMixin, LabMixin, SoftDeleteMixin, Base):
    __tablename__ = "research"
    __table_args__ = (
        Index("research_research_sample_id", "sample_id"),
        Index("research_research_research_goal_id", "research_goal_id"),
        Index("research_research_lab_id", "lab_id"),
        Index("research_research_status_id", "status_id"),
        Index("research_research_received_at", "received_at"),
        Index("research_research_completed_at", "completed_at"),
        Index("research_research_deleted_at", "deleted_at"),
        Index(
            "research_research_active_created_at",
            text("created_at DESC"),
            "id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "research_research_active_id",
            "id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=new_uuid7,
    )
    sample_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("samples.id", name="fk_research_sample_id_samples_id"),
        nullable=False,
    )
    research_goal_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "research_goals.id",
            name="fk_research_research_goal_id_research_goals_id",
        ),
        nullable=False,
    )
    comment: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(Text)
    status_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("research_statuses.id", name="fk_research_status_id_research_statuses_id"),
    )
    created_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", name="fk_research_created_by_users_id"),
    )
    updated_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", name="fk_research_updated_by_users_id"),
    )
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
