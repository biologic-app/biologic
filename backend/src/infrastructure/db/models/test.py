from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
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


class Test(TenantMixin, LabMixin, SoftDeleteMixin, Base):
    __tablename__ = "tests"
    __table_args__ = (
        Index("tests_tests_research_id", "research_id"),
        Index("tests_tests_indicator_id", "indicator_id"),
        Index("tests_tests_status_id", "status_id"),
        Index("tests_tests_is_active", "is_active"),
        Index("tests_tests_deleted_at", "deleted_at"),
        Index(
            "tests_tests_active_created_at",
            text("created_at DESC"),
            "id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "tests_tests_active_id",
            "id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=new_uuid7,
    )
    value: Mapped[str | None] = mapped_column(Text)
    comment: Mapped[str | None] = mapped_column(Text)
    norm: Mapped[str | None] = mapped_column(Text)
    verdict: Mapped[bool | None] = mapped_column(Boolean)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    research_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("research.id", name="fk_tests_research_id_research_id"),
        nullable=False,
    )
    indicator_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("indicators.id", name="fk_tests_indicator_id_indicators_id"),
    )
    status_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("test_statuses.id", name="fk_tests_status_id_test_statuses_id"),
    )
    created_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", name="fk_tests_created_by_users_id"),
    )
    updated_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", name="fk_tests_updated_by_users_id"),
    )
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
