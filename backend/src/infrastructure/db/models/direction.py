from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.models.base import Base


class Direction(Base):
    __tablename__ = "directions"
    __table_args__ = (
        Index("directions_directions_year_no", "year_no"),
        Index(
            "directions_directions_year_no_base_no",
            "year_no",
            "base_no",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("directions_directions_doctor_id", "doctor_id"),
        Index("directions_directions_object_id", "object_id"),
        Index("directions_directions_status_id", "status_id"),
        Index("directions_directions_is_urgent", "is_urgent"),
        Index("directions_directions_sampled_at", "sampled_at"),
        Index("directions_directions_received_at", "received_at"),
        Index("directions_directions_completed_at", "completed_at"),
        Index("directions_directions_deleted_at", "deleted_at"),
        Index(
            "directions_directions_active_created_at",
            text("created_at DESC"),
            "id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuidv7()"),
    )
    year_no: Mapped[int] = mapped_column(Integer, nullable=False)
    base_no: Mapped[int | None] = mapped_column(Integer)
    is_done: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    is_urgent: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    doctor_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("doctors.id", name="fk_directions_doctor_id_doctors_id"),
    )
    object_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("objects.id", name="fk_directions_object_id_objects_id"),
    )
    status_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("direction_statuses.id", name="fk_directions_status_id_direction_statuses_id"),
    )
    created_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", name="fk_directions_created_by_users_id"),
    )
    updated_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", name="fk_directions_updated_by_users_id"),
    )
    sampled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    import_warnings: Mapped[dict[str, object] | None] = mapped_column(JSONB)
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
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
