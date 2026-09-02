from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.uuid7 import new_uuid7
from src.infrastructure.db.models.base import Base
from src.infrastructure.db.models.mixins import TenantMixin


class WorkflowAttachment(TenantMixin, Base):
    """A file attached to a workflow run field, stored inline as bytea.

    ``storage`` is fixed to ``'db'`` for the MVP; the column leaves room for an
    object-storage backend later without a schema change.
    """

    __tablename__ = "workflow_attachments"
    __table_args__ = (Index("ix_workflow_attachments_run_id", "run_id"),)

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=new_uuid7,
    )
    run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("workflow_runs.id", name="fk_workflow_attachments_run_id"),
        nullable=False,
    )
    field_id: Mapped[str] = mapped_column(Text, nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str | None] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'db'"),
    )
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
