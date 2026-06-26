from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID

import httpx
from fastapi import FastAPI
from pytest import MonkeyPatch

from src.app_factory import create_app
from src.contexts.notifications.application.service import NotificationRecord
from src.contexts.notifications.presentation.router import get_notification_service
from src.core.config import get_settings
from src.core.pagination import PaginationParams, get_pagination_params


class FakeNotificationService:
    def __init__(self) -> None:
        self.marked_read: list[UUID] = []

    async def list_notifications(
        self,
        *,
        params: PaginationParams,
        status: str,
    ) -> tuple[list[NotificationRecord], int]:
        read_at = datetime(2026, 6, 2, 9, 0, tzinfo=UTC) if status == "read" else None
        return (
            [
                NotificationRecord(
                    id=UUID("00000000-0000-0000-0000-000000000201"),
                    kind="workflow.sample_registered",
                    title="Sample registered",
                    message="Sample was registered.",
                    entity_type="samples",
                    entity_id=UUID("00000000-0000-0000-0000-000000000202"),
                    source_event_type="SampleRegistered",
                    payload={"to_code": "registered"},
                    read_at=read_at,
                    created_at=datetime(2026, 6, 2, 8, 0, tzinfo=UTC),
                    target_user_id=None,
                    target_role_key=None,
                ),
            ],
            1,
        )

    async def mark_read(self, notification_id: UUID) -> NotificationRecord:
        self.marked_read.append(notification_id)
        return NotificationRecord(
            id=notification_id,
            kind="workflow.sample_registered",
            title="Sample registered",
            message="Sample was registered.",
            entity_type="samples",
            entity_id=UUID("00000000-0000-0000-0000-000000000202"),
            source_event_type="SampleRegistered",
            payload={},
            read_at=datetime(2026, 6, 2, 10, 0, tzinfo=UTC),
            created_at=datetime(2026, 6, 2, 8, 0, tzinfo=UTC),
            target_user_id=None,
            target_role_key=None,
        )

    async def stream_after(
        self,
        *,
        last_seen: datetime,
        poll_interval_seconds: float,
    ) -> AsyncIterator[NotificationRecord]:
        yield NotificationRecord(
            id=UUID("00000000-0000-0000-0000-000000000203"),
            kind="workflow.sample_rejected",
            title="Sample rejected",
            message="Sample was rejected.",
            entity_type="samples",
            entity_id=UUID("00000000-0000-0000-0000-000000000204"),
            source_event_type="SampleRejected",
            payload={},
            read_at=None,
            created_at=datetime(2026, 6, 2, 11, 0, tzinfo=UTC),
            target_user_id=None,
            target_role_key=None,
        )


def _app(monkeypatch: MonkeyPatch) -> tuple[FastAPI, FakeNotificationService]:
    monkeypatch.setenv("APP_DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
    monkeypatch.setenv("APP_JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("APP_AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("APP_AUTH_COOKIE_DOMAIN", "localhost")
    get_settings.cache_clear()
    app = create_app()
    service = FakeNotificationService()

    async def override_notification_service() -> FakeNotificationService:
        return service

    async def override_pagination_params() -> PaginationParams:
        return PaginationParams(limit=25)

    app.dependency_overrides[get_notification_service] = override_notification_service
    app.dependency_overrides[get_pagination_params] = override_pagination_params
    return app, service


async def _request(
    monkeypatch: MonkeyPatch,
    method: str,
    path: str,
    *,
    json: dict[str, object] | None = None,
) -> tuple[httpx.Response, FakeNotificationService]:
    try:
        app, service = _app(monkeypatch)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.request(method, path, json=json), service
    finally:
        get_settings.cache_clear()


async def test_list_alerts_returns_real_notification_contract(monkeypatch: MonkeyPatch) -> None:
    response, _service = await _request(monkeypatch, "GET", "/api/v1/alerts?status=unread")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["id"] == "00000000-0000-0000-0000-000000000201"
    assert payload["items"][0]["title"] == "Sample registered"
    assert payload["items"][0]["read_at"] is None
    assert payload["items"][0]["target_user_id"] is None
    assert payload["items"][0]["target_role_key"] is None
    assert payload["meta"]["total"] == 1


async def test_mark_alert_read_sets_read_at(monkeypatch: MonkeyPatch) -> None:
    response, service = await _request(
        monkeypatch,
        "POST",
        "/api/v1/alerts/00000000-0000-0000-0000-000000000201/mark-read",
        json={"actor_id": "00000000-0000-0000-0000-000000000001"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["read_at"] == "2026-06-02T10:00:00Z"
    assert service.marked_read == [UUID("00000000-0000-0000-0000-000000000201")]


async def test_alert_stream_emits_notification_created_sse(monkeypatch: MonkeyPatch) -> None:
    response, _service = await _request(monkeypatch, "GET", "/api/v1/alerts/stream")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: notification.created" in response.text
    assert '"id":"00000000-0000-0000-0000-000000000203"' in response.text
