from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.uuid7 import new_uuid7
from src.infrastructure.db.models.base import Base
from src.infrastructure.db.models.mixins import SoftDeleteMixin, TenantMixin


class Protocol(TenantMixin, SoftDeleteMixin, Base):
    __tablename__ = "protocols"
    __table_args__ = (
        Index("protocols_protocols_year_no", "year_no"),
        Index("protocols_protocols_conclusion_id", "conclusion_id"),
        Index("protocols_protocols_protocol_type_id", "protocol_type_id"),
        Index("protocols_protocols_issued_at", "issued_at"),
        Index("protocols_protocols_deleted_at", "deleted_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=new_uuid7,
    )
    year_no: Mapped[int] = mapped_column(Integer, nullable=False)
    copies: Mapped[int | None] = mapped_column(SmallInteger)
    is_signed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    protocol_copy_name: Mapped[str | None] = mapped_column(Text)
    excerpt_copy_name: Mapped[str | None] = mapped_column(Text)
    conclusion_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("conclusions.id", name="fk_protocols_conclusion_id_conclusions_id"),
    )
    protocol_type_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("protocol_types.id", name="fk_protocols_protocol_type_id_protocol_types_id"),
    )
    created_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", name="fk_protocols_created_by_users_id"),
    )
    updated_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", name="fk_protocols_updated_by_users_id"),
    )
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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
