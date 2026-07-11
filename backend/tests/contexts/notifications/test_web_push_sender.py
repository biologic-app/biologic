from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from types import TracebackType
from typing import Self, cast
from uuid import UUID

import pytest
from pywebpush import WebPushException

from src.contexts.notifications.application.push_ports import PushSubscriptionRecord
from src.contexts.notifications.application.service import NotificationRecord
from src.contexts.notifications.infrastructure import push_sender as push_sender_module
from src.contexts.notifications.infrastructure.push_sender import WebPushSender
from src.core.config import Settings

USER_ID = UUID("00000000-0000-0000-0000-000000000c01")

RECORD = NotificationRecord(
    id=UUID("00000000-0000-0000-0000-000000000c02"),
    kind="workflow.sample_registered",
    title="Sample registered",
    message="Sample was registered.",
    entity_type="samples",
    entity_id=UUID("00000000-0000-0000-0000-000000000c03"),
    source_event_type="SampleRegistered",
    payload={},
    read_at=None,
    created_at=datetime(2026, 7, 10, 9, 0, tzinfo=UTC),
    target_user_id=USER_ID,
    target_role_key=None,
)

SUBSCRIPTION = PushSubscriptionRecord(
    id=UUID("00000000-0000-0000-0000-000000000c04"),
    user_id=USER_ID,
    endpoint="https://push.example/endpoint-1",
    p256dh="p256dh-key",
    auth="auth-key",
)


class FakeSession:
    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None


class FakeSessionFactory:
    def __init__(self) -> None:
        self.opened = 0

    def __call__(self) -> FakeSession:
        self.opened += 1
        return FakeSession()


class FakeStore:
    def __init__(self, subscriptions: list[PushSubscriptionRecord]) -> None:
        self._subscriptions = subscriptions
        self.deleted_endpoints: list[str] = []

    async def list_for_users(self, user_ids: Iterable[UUID]) -> list[PushSubscriptionRecord]:
        user_ids = set(user_ids)
        return [s for s in self._subscriptions if s.user_id in user_ids]

    async def delete_by_endpoint(self, endpoint: str) -> None:
        self.deleted_endpoints.append(endpoint)

    async def upsert(self, **kwargs: object) -> PushSubscriptionRecord:
        raise AssertionError("upsert should not be called by the sender")


def _settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://user:pass@localhost:5432/test",
        jwt_secret_key="test-secret",
        auth_cookie_secure=False,
        auth_cookie_domain="localhost",
        vapid_public_key="public",
        vapid_private_key="private",
        vapid_subject="mailto:admin@example.com",
    )


async def test_send_many_is_a_noop_when_no_record_has_a_target_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_factory = FakeSessionFactory()
    sender = WebPushSender(session_factory=session_factory, settings=_settings())  # type: ignore[arg-type]

    untargeted = NotificationRecord(
        id=UUID("00000000-0000-0000-0000-000000000c05"),
        kind="workflow.sample_registered",
        title="t",
        message="m",
        entity_type="samples",
        entity_id=UUID("00000000-0000-0000-0000-000000000c06"),
        source_event_type="SampleRegistered",
        payload={},
        read_at=None,
        created_at=datetime(2026, 7, 10, 9, 0, tzinfo=UTC),
        target_user_id=None,
        target_role_key=None,
    )

    await sender.send_many([untargeted])

    assert session_factory.opened == 0


async def test_send_many_delivers_one_push_per_subscription(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    def fake_webpush(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(push_sender_module, "webpush", fake_webpush)
    store = FakeStore([SUBSCRIPTION])
    sender = WebPushSender(
        session_factory=FakeSessionFactory(),  # type: ignore[arg-type]
        settings=_settings(),
        store_factory=lambda _session: store,
    )

    await sender.send_many([RECORD])

    assert len(calls) == 1
    subscription_info = cast(dict[str, object], calls[0]["subscription_info"])
    assert subscription_info["endpoint"] == SUBSCRIPTION.endpoint
    assert calls[0]["vapid_claims"] == {"sub": "mailto:admin@example.com"}
    assert store.deleted_endpoints == []


async def test_expired_subscription_is_deleted_on_410(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        status_code = 410

    def failing_webpush(**kwargs: object) -> None:
        raise WebPushException("gone", response=FakeResponse())

    monkeypatch.setattr(push_sender_module, "webpush", failing_webpush)
    store = FakeStore([SUBSCRIPTION])
    sender = WebPushSender(
        session_factory=FakeSessionFactory(),  # type: ignore[arg-type]
        settings=_settings(),
        store_factory=lambda _session: store,
    )

    await sender.send_many([RECORD])

    assert store.deleted_endpoints == [SUBSCRIPTION.endpoint]


async def test_non_expiry_failure_does_not_delete_the_subscription(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        status_code = 500

    def failing_webpush(**kwargs: object) -> None:
        raise WebPushException("server error", response=FakeResponse())

    monkeypatch.setattr(push_sender_module, "webpush", failing_webpush)
    store = FakeStore([SUBSCRIPTION])
    sender = WebPushSender(
        session_factory=FakeSessionFactory(),  # type: ignore[arg-type]
        settings=_settings(),
        store_factory=lambda _session: store,
    )

    await sender.send_many([RECORD])

    assert store.deleted_endpoints == []
