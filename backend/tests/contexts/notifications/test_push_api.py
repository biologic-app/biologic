from collections.abc import Iterable
from datetime import timedelta
from uuid import UUID

import httpx
from fastapi import FastAPI
from pytest import MonkeyPatch

from src.app_factory import create_app
from src.contexts.notifications.application.push_ports import PushSubscriptionRecord
from src.contexts.notifications.presentation.push_router import get_push_subscription_store
from src.core.config import get_settings
from src.core.security import encode_jwt_token

VIEWER_ID = UUID("00000000-0000-0000-0000-0000000000a1")
SUBSCRIPTION_ID = UUID("00000000-0000-0000-0000-0000000000a2")
ENDPOINT = "https://push.example/endpoint"


class FakePushSubscriptionStore:
    def __init__(self) -> None:
        self.upserted: list[dict[str, object]] = []
        self.deleted: list[str] = []

    async def upsert(
        self,
        *,
        user_id: UUID,
        endpoint: str,
        p256dh: str,
        auth: str,
        user_agent: str | None,
    ) -> PushSubscriptionRecord:
        self.upserted.append(
            {
                "user_id": user_id,
                "endpoint": endpoint,
                "p256dh": p256dh,
                "auth": auth,
                "user_agent": user_agent,
            },
        )
        return PushSubscriptionRecord(
            id=SUBSCRIPTION_ID, user_id=user_id, endpoint=endpoint, p256dh=p256dh, auth=auth
        )

    async def delete_by_endpoint(self, endpoint: str) -> None:
        self.deleted.append(endpoint)

    async def list_for_users(self, user_ids: Iterable[UUID]) -> list[PushSubscriptionRecord]:
        raise AssertionError("list_for_users should not be called from the router")


def _app(monkeypatch: MonkeyPatch) -> tuple[FastAPI, FakePushSubscriptionStore]:
    monkeypatch.setenv("APP_DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
    monkeypatch.setenv("APP_JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("APP_AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("APP_AUTH_COOKIE_DOMAIN", "localhost")
    monkeypatch.setenv("APP_VAPID_PUBLIC_KEY", "test-vapid-public-key")
    get_settings.cache_clear()
    app = create_app()
    store = FakePushSubscriptionStore()

    async def override_store() -> FakePushSubscriptionStore:
        return store

    app.dependency_overrides[get_push_subscription_store] = override_store
    return app, store


async def _request(
    monkeypatch: MonkeyPatch,
    method: str,
    path: str,
    *,
    json: dict[str, object] | None = None,
    authenticated: bool = True,
) -> tuple[httpx.Response, FakePushSubscriptionStore]:
    try:
        app, store = _app(monkeypatch)
        settings = get_settings()
        cookies = {}
        if authenticated:
            token, _expires_at = encode_jwt_token(
                subject=VIEWER_ID,
                token_type="access",
                secret_key=settings.jwt_secret_key,
                algorithm=settings.jwt_algorithm,
                expires_delta=timedelta(hours=1),
            )
            cookies = {settings.access_cookie_name: token}
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver", cookies=cookies
        ) as client:
            return await client.request(method, path, json=json), store
    finally:
        get_settings.cache_clear()


async def test_vapid_public_key_is_public_and_returns_the_configured_key(
    monkeypatch: MonkeyPatch,
) -> None:
    response, _store = await _request(
        monkeypatch, "GET", "/api/v1/push/vapid-public-key", authenticated=False
    )

    assert response.status_code == 200
    assert response.json() == {"public_key": "test-vapid-public-key"}


async def test_create_subscription_upserts_for_the_authenticated_user(
    monkeypatch: MonkeyPatch,
) -> None:
    response, store = await _request(
        monkeypatch,
        "POST",
        "/api/v1/push/subscriptions",
        json={"endpoint": ENDPOINT, "keys": {"p256dh": "p", "auth": "a"}},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["data"]["id"] == str(SUBSCRIPTION_ID)
    assert payload["data"]["endpoint"] == ENDPOINT
    assert len(store.upserted) == 1
    upserted = store.upserted[0]
    assert upserted["user_id"] == VIEWER_ID
    assert upserted["endpoint"] == ENDPOINT
    assert upserted["p256dh"] == "p"
    assert upserted["auth"] == "a"
    # httpx's ASGITransport sends its own default User-Agent header; only the
    # plumbing (request.headers -> repository.upsert) matters here.
    assert upserted["user_agent"]


async def test_create_subscription_requires_authentication(monkeypatch: MonkeyPatch) -> None:
    response, _store = await _request(
        monkeypatch,
        "POST",
        "/api/v1/push/subscriptions",
        json={"endpoint": ENDPOINT, "keys": {"p256dh": "p", "auth": "a"}},
        authenticated=False,
    )

    assert response.status_code == 401


async def test_delete_subscription_removes_the_endpoint(monkeypatch: MonkeyPatch) -> None:
    response, store = await _request(
        monkeypatch,
        "DELETE",
        "/api/v1/push/subscriptions",
        json={"endpoint": ENDPOINT},
    )

    assert response.status_code == 204
    assert store.deleted == [ENDPOINT]
