import asyncio
from collections.abc import Iterable
from datetime import UTC, datetime
from uuid import UUID

from src.contexts.notifications.application.push_dispatcher import PushDispatcher
from src.contexts.notifications.application.service import NotificationRecord

TARGET_USER_ID = UUID("00000000-0000-0000-0000-000000000d01")

RECORD = NotificationRecord(
    id=UUID("00000000-0000-0000-0000-000000000d02"),
    kind="workflow.sample_registered",
    title="Sample registered",
    message="Sample was registered.",
    entity_type="samples",
    entity_id=UUID("00000000-0000-0000-0000-000000000d03"),
    source_event_type="SampleRegistered",
    payload={},
    read_at=None,
    created_at=datetime(2026, 7, 10, 9, 0, tzinfo=UTC),
    target_user_id=TARGET_USER_ID,
    target_role_key=None,
)

UNTARGETED_RECORD = NotificationRecord(
    id=UUID("00000000-0000-0000-0000-000000000d04"),
    kind="workflow.sample_registered",
    title="Sample registered",
    message="Sample was registered.",
    entity_type="samples",
    entity_id=UUID("00000000-0000-0000-0000-000000000d05"),
    source_event_type="SampleRegistered",
    payload={},
    read_at=None,
    created_at=datetime(2026, 7, 10, 9, 0, tzinfo=UTC),
    target_user_id=None,
    target_role_key="role:lab_doctor",
)


class RecordingSender:
    def __init__(self) -> None:
        self.calls: list[list[NotificationRecord]] = []

    async def send_many(self, records: Iterable[NotificationRecord]) -> None:
        self.calls.append(list(records))


async def test_dispatch_schedules_a_background_send_for_targeted_records() -> None:
    sender = RecordingSender()
    dispatcher = PushDispatcher(sender=sender)

    dispatcher.dispatch([RECORD])
    await dispatcher.drain()

    assert sender.calls == [[RECORD]]


async def test_dispatch_drops_records_with_no_target_user() -> None:
    sender = RecordingSender()
    dispatcher = PushDispatcher(sender=sender)

    dispatcher.dispatch([UNTARGETED_RECORD])
    await dispatcher.drain()

    assert sender.calls == []


async def test_dispatch_is_a_noop_for_an_empty_outbox() -> None:
    sender = RecordingSender()
    dispatcher = PushDispatcher(sender=sender)

    dispatcher.dispatch([])
    await dispatcher.drain()

    assert sender.calls == []


async def test_drain_waits_for_slow_sends_without_raising() -> None:
    class SlowFailingSender:
        async def send_many(self, records: Iterable[NotificationRecord]) -> None:
            await asyncio.sleep(0)
            raise RuntimeError("push provider unavailable")

    dispatcher = PushDispatcher(sender=SlowFailingSender())

    dispatcher.dispatch([RECORD])
    await dispatcher.drain()  # must not raise: gather uses return_exceptions=True

    assert dispatcher._tasks == set()
