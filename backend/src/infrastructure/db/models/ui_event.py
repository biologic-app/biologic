from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.uuid7 import new_uuid7
from src.infrastructure.db.models.base import Base
from src.infrastructure.db.models.mixins import TenantMixin


class UiEvent(TenantMixin, Base):
    """Passive UI telemetry event (ROADMAP A2.3).

    Anonymous-by-design: only element/session identifiers are stored, never
    form values or other user-entered content.

    Partitioning: `ui_events` is expected to grow quickly (one row per UI
    interaction), so it should eventually become a PostgreSQL native range
    partitioned table keyed on `created_at` (e.g. monthly partitions) with an
    automated retention job dropping partitions older than the retention
    window (TODO — not implemented yet; see migration
    `20260709_0018_ui_events_telemetry.py` for the plain-table placeholder).
    Retention policy: raw events are only needed for short-term UX analysis
    and should not be kept indefinitely (TODO: wire a scheduled cleanup once
    the retention window is decided, e.g. 90 days).
    """

    __tablename__ = "ui_events"
    __table_args__ = (
        Index("ui_events_ui_events_created_at", "created_at"),
        Index("ui_events_ui_events_session_id", "session_id"),
        Index("ui_events_ui_events_event", "event"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=new_uuid7,
    )
    event: Mapped[str] = mapped_column(Text, nullable=False)
    element_id: Mapped[str | None] = mapped_column(Text)
    route: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str | None] = mapped_column(Text)
    session_id: Mapped[str] = mapped_column(Text, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
