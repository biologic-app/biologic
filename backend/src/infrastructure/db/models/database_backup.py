from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.uuid7 import new_uuid7
from src.infrastructure.db.models.base import Base
from src.infrastructure.db.models.mixins import TenantMixin


class DatabaseBackup(TenantMixin, Base):
    """Registry row for one full-database dump kept on the filesystem.

    PostgreSQL stores only the metadata — ``file_path`` above all; the dump
    payload itself never lives in a table. Deleting a row therefore does not
    free the bytes, so the router removes the file alongside the record.

    The table is excluded from every dump it describes (see
    ``src.application.data_transfer``): a restore must not wipe the registry
    that points at the file being restored.
    """

    __tablename__ = "database_backups"
    __table_args__ = (Index("ix_database_backups_created_at", "created_at"),)

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=new_uuid7,
    )
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    # "custom" — pg_dump archive; "sql" — plain INSERT script (see engines).
    format: Mapped[str] = mapped_column(Text, nullable=False)
    # "export" — produced here; "upload" — brought in from outside.
    origin: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'export'"))
    # "in_progress" | "completed" | "failed"
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'in_progress'"))
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    restored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    restored_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    # "completed" | "failed" | NULL when never restored.
    restore_status: Mapped[str | None] = mapped_column(Text)
    restore_error: Mapped[str | None] = mapped_column(Text)
