from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from src.contexts.laboratory_workflow.domain.events import DomainEvent
from src.contexts.notifications.domain.contracts import NotificationDraft, notification_from_event
from src.core.pagination import PaginationParams


@dataclass(frozen=True)
class NotificationRecord:
    id: UUID
    kind: str
    title: str
    message: str
    entity_type: str
    entity_id: UUID
    source_event_type: str
    payload: dict[str, Any]
    read_at: datetime | None
    created_at: datetime
    target_user_id: UUID | None
    target_role_key: str | None


class NotificationRepository(Protocol):
    async def create_many(
        self,
        drafts: Iterable[NotificationDraft],
    ) -> list[NotificationRecord]: ...

    async def list(
        self,
        *,
        params: PaginationParams,
        status: str,
        created_after: datetime | None = None,
    ) -> tuple[list[NotificationRecord], int]: ...

    async def mark_read(self, notification_id: UUID, read_at: datetime) -> NotificationRecord: ...


class NotificationService:
    def __init__(self, *, repository: NotificationRepository) -> None:
        self.repository = repository

    async def create_from_events(self, events: Iterable[DomainEvent]) -> list[NotificationRecord]:
        drafts = [
            draft
            for event in events
            if (draft := notification_from_event(event)) is not None
        ]
        if not drafts:
            return []
        return await self.repository.create_many(drafts)

    async def list_notifications(
        self,
        *,
        params: PaginationParams,
        status: str,
    ) -> tuple[list[NotificationRecord], int]:
        return await self.repository.list(params=params, status=status)

    async def mark_read(self, notification_id: UUID) -> NotificationRecord:
        return await self.repository.mark_read(notification_id, datetime.now(UTC))

    async def stream_after(
        self,
        *,
        last_seen: datetime,
        poll_interval_seconds: float = 1.0,
    ) -> AsyncIterator[NotificationRecord]:
        cursor = last_seen
        params = PaginationParams(limit=100, sort_order="asc")
        while True:
            records, _total = await self.repository.list(
                params=params,
                status="all",
                created_after=cursor,
            )
            for record in records:
                cursor = max(cursor, record.created_at)
                yield record
            await asyncio.sleep(poll_interval_seconds)
