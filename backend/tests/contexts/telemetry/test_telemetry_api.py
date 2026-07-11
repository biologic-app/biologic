from collections.abc import Iterable

import httpx
from fastapi import FastAPI
from pytest import MonkeyPatch

from src.app_factory import create_app
from src.contexts.telemetry.application.service import TelemetryService
from src.contexts.telemetry.domain.contracts import TelemetryEventDraft
from src.contexts.telemetry.presentation.router import get_telemetry_service
from src.core.config import get_settings


class FakeTelemetryRepository:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.received: list[TelemetryEventDraft] = []

    async def create_many(self, drafts: Iterable[TelemetryEventDraft]) -> None:
        if self.fail:
            raise RuntimeError("boom")
        self.received.extend(drafts)


def _app(
    monkeypatch: MonkeyPatch, *, fail: bool = False
) -> tuple[FastAPI, FakeTelemetryRepository]:
    monkeypatch.setenv("APP_DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
    monkeypatch.setenv("APP_JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("APP_AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("APP_AUTH_COOKIE_DOMAIN", "localhost")
    get_settings.cache_clear()
    app = create_app()
    repository = FakeTelemetryRepository(fail=fail)

    async def override_telemetry_service() -> TelemetryService:
        return TelemetryService(repository=repository)

    app.dependency_overrides[get_telemetry_service] = override_telemetry_service
    return app, repository


async def test_record_telemetry_events_accepts_batch(monkeypatch: MonkeyPatch) -> None:
    try:
        app, repository = _app(monkeypatch)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/telemetry/events",
                json={
                    "events": [
                        {
                            "event": "click",
                            "route": "/directions",
                            "session_id": "session-1",
                            "ts": "2026-07-09T10:00:00Z",
                            "element_id": "direction-create-button",
                            "role": "lab_technician",
                        },
                        {
                            "event": "navigation",
                            "route": "/samples",
                            "session_id": "session-1",
                            "ts": "2026-07-09T10:00:05Z",
                        },
                    ],
                },
            )

        assert response.status_code == 202
        payload = response.json()
        assert payload["data"]["accepted"] == 2
        assert payload["meta"]["operation"] == "telemetry.record_events"
        assert len(repository.received) == 2
        assert repository.received[0].event == "click"
        assert repository.received[0].element_id == "direction-create-button"
        assert repository.received[1].role is None
    finally:
        get_settings.cache_clear()


async def test_record_telemetry_events_rejects_empty_batch(monkeypatch: MonkeyPatch) -> None:
    try:
        app, _repository = _app(monkeypatch)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post("/api/v1/telemetry/events", json={"events": []})

        assert response.status_code == 422
    finally:
        get_settings.cache_clear()


async def test_record_telemetry_events_swallows_repository_failure(
    monkeypatch: MonkeyPatch,
) -> None:
    try:
        app, repository = _app(monkeypatch, fail=True)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/telemetry/events",
                json={
                    "events": [
                        {
                            "event": "click",
                            "route": "/directions",
                            "session_id": "session-1",
                            "ts": "2026-07-09T10:00:00Z",
                        },
                    ],
                },
            )

        assert response.status_code == 202
        assert response.json()["data"]["accepted"] == 0
        assert repository.received == []
    finally:
        get_settings.cache_clear()
