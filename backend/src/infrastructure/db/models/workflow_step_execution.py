from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.uuid7 import new_uuid7
from src.infrastructure.db.models.base import Base
from src.infrastructure.db.models.mixins import TenantMixin


class WorkflowStepExecution(TenantMixin, Base):
    """Idempotency guard for ``execute-step``.

    A row records that ``(run_id, node_id, attempt)`` was applied together with
    its result. The unique constraint makes a replay of the same attempt a
    no-op that returns the stored result instead of mutating again.
    """

    __tablename__ = "workflow_step_executions"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "node_id",
            "attempt",
            name="uq_workflow_step_executions_run_node_attempt",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=new_uuid7,
    )
    run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("workflow_runs.id", name="fk_workflow_step_executions_run_id"),
        nullable=False,
    )
    node_id: Mapped[str] = mapped_column(Text, nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
