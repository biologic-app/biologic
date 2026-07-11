from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from src.contexts.notifications.application.service import NotificationRecord


@dataclass(frozen=True)
class PushSubscriptionRecord:
    id: UUID
    user_id: UUID
    endpoint: str
    p256dh: str
    auth: str


class PushSubscriptionStore(Protocol):
    async def upsert(
        self,
        *,
        user_id: UUID,
        endpoint: str,
        p256dh: str,
        auth: str,
        user_agent: str | None,
    ) -> PushSubscriptionRecord: ...

    async def delete_by_endpoint(self, endpoint: str) -> None: ...

    async def list_for_users(self, user_ids: Iterable[UUID]) -> list[PushSubscriptionRecord]: ...


class PushSender(Protocol):
    """Delivers already-persisted notifications as OS-level push messages.

    Called from PushDispatcher's fire-and-forget task, after the triggering
    transaction has committed — never from inside a request/response path.
    """

    async def send_many(self, records: Iterable[NotificationRecord]) -> None: ...
