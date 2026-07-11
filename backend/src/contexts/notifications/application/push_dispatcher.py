from __future__ import annotations

import asyncio
from collections.abc import Iterable

from src.contexts.notifications.application.push_ports import PushSender
from src.contexts.notifications.application.service import NotificationRecord


class PushDispatcher:
    """Fire-and-forget push delivery, decoupled from the request/response cycle.

    dispatch() must only be called after the triggering Unit of Work has
    committed — calling it earlier would push notifications for a workflow
    change that later fails to commit and is never actually persisted.
    Background tasks are tracked so `drain()` can await them during shutdown
    instead of letting the event loop kill them mid-send.
    """

    def __init__(self, *, sender: PushSender) -> None:
        self._sender = sender
        self._tasks: set[asyncio.Task[None]] = set()

    def dispatch(self, records: Iterable[NotificationRecord]) -> None:
        records = [record for record in records if record.target_user_id is not None]
        if not records:
            return
        task = asyncio.create_task(self._sender.send_many(records))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def drain(self) -> None:
        if not self._tasks:
            return
        await asyncio.gather(*self._tasks, return_exceptions=True)
