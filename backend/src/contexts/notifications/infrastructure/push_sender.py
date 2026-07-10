from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from collections.abc import Callable, Iterable

from pywebpush import WebPushException, webpush
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.contexts.notifications.application.push_ports import (
    PushSubscriptionRecord,
    PushSubscriptionStore,
)
from src.contexts.notifications.application.service import NotificationRecord
from src.contexts.notifications.infrastructure.push_subscription_repository import (
    SqlAlchemyPushSubscriptionStore,
)
from src.core.config import Settings


class WebPushSender:
    """Sends one Web Push message per (subscription, notification) pair.

    Opens its own DB session per call instead of reusing a request-scoped
    one: this runs from a background task started by PushDispatcher, well
    after the originating request's session has been closed.
    """

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
        store_factory: Callable[[AsyncSession], PushSubscriptionStore] = (
            lambda session: SqlAlchemyPushSubscriptionStore(session=session)
        ),
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings
        self._store_factory = store_factory

    async def send_many(self, records: Iterable[NotificationRecord]) -> None:
        records = [record for record in records if record.target_user_id is not None]
        if not records:
            return
        user_ids = {record.target_user_id for record in records if record.target_user_id}

        async with self._session_factory() as session:
            store = self._store_factory(session)
            subscriptions = await store.list_for_users(user_ids)
            if not subscriptions:
                return

            subscriptions_by_user: dict[object, list[PushSubscriptionRecord]] = defaultdict(list)
            for subscription in subscriptions:
                subscriptions_by_user[subscription.user_id].append(subscription)

            results = await asyncio.gather(
                *(
                    self._send_one(subscription, record)
                    for record in records
                    for subscription in subscriptions_by_user.get(record.target_user_id, [])
                ),
                return_exceptions=True,
            )
            for expired_endpoint in results:
                if isinstance(expired_endpoint, str):
                    await store.delete_by_endpoint(expired_endpoint)

    async def _send_one(
        self, subscription: PushSubscriptionRecord, record: NotificationRecord
    ) -> str | None:
        payload = json.dumps({"title": record.title, "body": record.message, "url": "/alerts"})
        try:
            await asyncio.to_thread(
                webpush,
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
                },
                data=payload,
                vapid_private_key=self._settings.vapid_private_key,
                vapid_claims={"sub": self._settings.vapid_subject},
            )
        except WebPushException as exc:
            response = exc.response
            status_code = response.status_code if response is not None else None
            if status_code in (404, 410):
                return subscription.endpoint
        return None
