from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.uuid7 import new_uuid7
from src.infrastructure.db.models.base import Base
from src.infrastructure.db.models.mixins import TenantMixin


class WorkflowSchemaVersion(TenantMixin, Base):
    """An immutable committed schema of a workflow template.

    Versions are append-only: once created they are never mutated. The
    ``(template_id, version)`` pair is unique.
    """

    __tablename__ = "workflow_schema_versions"
    __table_args__ = (
        UniqueConstraint(
            "template_id",
            "version",
            name="uq_workflow_schema_versions_template_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=new_uuid7,
    )
    template_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "workflow_templates.id",
            name="fk_wf_schema_versions_template_id",
        ),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    schema: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
