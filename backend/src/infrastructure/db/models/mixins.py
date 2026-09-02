from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column


class TenantMixin:
    """Optional branch scope (the application's tenant boundary)."""

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))


class OwnerMixin:
    """Optional owner reference stored without a database-level FK."""

    owner_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))


class LabMixin:
    """Optional laboratory scope stored without a database-level FK."""

    lab_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))


class SoftDeleteMixin:
    """Timestamp-based soft deletion shared by mutable domain entities."""

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def deleted(self) -> bool:
        return self.deleted_at is not None

    @deleted.setter
    def deleted(self, value: bool) -> None:
        self.deleted_at = datetime.now(UTC) if value else None

    def mark_deleted(self) -> None:
        self.deleted = True

    def restore(self) -> None:
        self.deleted = False


# Descriptive aliases for callers that prefer column-oriented names.
BranchMixin = TenantMixin
DeletedMixin = SoftDeleteMixin
