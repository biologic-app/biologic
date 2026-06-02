from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from uuid import UUID

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.notifications.application.service import NotificationRecord
from src.contexts.notifications.domain.contracts import NotificationDraft
from src.core.errors import NotFoundError
from src.core.pagination import PaginationParams
from src.infrastructure.db.models import Notification


class SqlAlchemyNotificationRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def create_many(self, drafts: Iterable[NotificationDraft]) -> list[NotificationRecord]:
        rows = [
            Notification(
                kind=draft.kind,
                title=draft.title,
                message=draft.message,
                entity_type=draft.entity_type,
                entity_id=draft.entity_id,
                source_event_type=draft.source_event_type,
                payload=draft.payload,
                target_user_id=draft.target_user_id,
                target_role_key=draft.target_role_key,
            )
            for draft in drafts
        ]
        self.session.add_all(rows)
        await self.session.commit()
        for row in rows:
            await self.session.refresh(row)
        return [self._record(row) for row in rows]

    async def list(
        self,
        *,
        params: PaginationParams,
        status: str,
        created_after: datetime | None = None,
    ) -> tuple[list[NotificationRecord], int]:
        filters = []
        if status == "unread":
            filters.append(Notification.read_at.is_(None))
        elif status == "read":
            filters.append(Notification.read_at.is_not(None))
        if created_after is not None:
            filters.append(Notification.created_at > created_after)

        total_result = await self.session.execute(
            select(func.count()).select_from(Notification).where(*filters),
        )
        total = int(total_result.scalar_one())
        order_by = (
            asc(Notification.created_at)
            if params.sort_order == "asc"
            else desc(Notification.created_at)
        )
        result = await self.session.execute(
            select(Notification).where(*filters).order_by(order_by).limit(params.limit),
        )
        return [self._record(row) for row in result.scalars().all()], total

    async def mark_read(self, notification_id: UUID, read_at: datetime) -> NotificationRecord:
        result = await self.session.execute(
            select(Notification).where(Notification.id == notification_id).with_for_update(),
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundError("Notification was not found.")
        if row.read_at is None:
            row.read_at = read_at
            await self.session.commit()
            await self.session.refresh(row)
        return self._record(row)

    def _record(self, row: Notification) -> NotificationRecord:
        return NotificationRecord(
            id=row.id,
            kind=row.kind,
            title=row.title,
            message=row.message,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            source_event_type=row.source_event_type,
            payload=row.payload or {},
            read_at=row.read_at,
            created_at=row.created_at,
            target_user_id=row.target_user_id,
            target_role_key=row.target_role_key,
        )
