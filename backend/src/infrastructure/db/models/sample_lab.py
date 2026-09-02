from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.uuid7 import new_uuid7
from src.infrastructure.db.models.base import Base
from src.infrastructure.db.models.mixins import LabMixin, SoftDeleteMixin, TenantMixin


class SampleLab(TenantMixin, LabMixin, SoftDeleteMixin, Base):
    """Sample ↔ laboratory assignment (many-to-many, soft-deletable).

    A sample belongs to one or more laboratories, derived at import time from
    the legacy Бак/Т-Х/Т-Б/РВ/ПЦР mark columns (each resolves to a ``labs``
    row by code). The (sample_id, lab_id) pair is unique only among live rows
    so an assignment can be soft-deleted and re-added later.
    """

    __tablename__ = "sample_labs"
    __table_args__ = (
        Index(
            "sample_labs_unique_pair",
            "sample_id",
            "lab_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("sample_labs_sample_id", "sample_id"),
        Index("sample_labs_lab_id", "lab_id"),
        Index("sample_labs_deleted_at", "deleted_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=new_uuid7,
    )
    sample_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "samples.id",
            name="fk_sample_labs_sample_id_samples_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    lab_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
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
