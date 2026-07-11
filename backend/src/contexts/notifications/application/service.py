from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from src.contexts.notifications.domain.contracts import NotificationDraft
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
        viewer_id: UUID,
        created_after: datetime | None = None,
    ) -> tuple[list[NotificationRecord], int]: ...

    async def mark_read(self, notification_id: UUID, read_at: datetime) -> NotificationRecord: ...


class NotificationService:
    def __init__(self, *, repository: NotificationRepository) -> None:
        self.repository = repository

    async def list_notifications(
        self,
        *,
        params: PaginationParams,
        status: str,
        viewer_id: UUID,
    ) -> tuple[list[NotificationRecord], int]:
        return await self.repository.list(params=params, status=status, viewer_id=viewer_id)

    async def mark_read(self, notification_id: UUID) -> NotificationRecord:
        return await self.repository.mark_read(notification_id, datetime.now(UTC))

    async def stream_after(
        self,
        *,
        last_seen: datetime,
        viewer_id: UUID,
        poll_interval_seconds: float = 1.0,
        shutdown: asyncio.Event | None = None,
    ) -> AsyncIterator[NotificationRecord]:
        cursor = last_seen
        params = PaginationParams(limit=100, sort_order="asc")
        while shutdown is None or not shutdown.is_set():
            records, _total = await self.repository.list(
                params=params,
                status="all",
                viewer_id=viewer_id,
                created_after=cursor,
            )
            for record in records:
                cursor = max(cursor, record.created_at)
                yield record
            if await _sleep_or_shutdown(poll_interval_seconds, shutdown):
                break


async def _sleep_or_shutdown(seconds: float, shutdown: asyncio.Event | None) -> bool:
    """Sleep up to ``seconds``; return True if shutdown was requested meanwhile.

    Racing the poll interval against the shutdown flag lets an open stream close
    the moment a termination signal arrives instead of after a full poll tick.
    """
    if shutdown is None:
        await asyncio.sleep(seconds)
        return False
    try:
        await asyncio.wait_for(shutdown.wait(), timeout=seconds)
    except TimeoutError:
        return False
    return True
