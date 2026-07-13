from datetime import timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from src.app_factory import create_app
from src.application.access_control.use_cases.auth import AuthSession
from src.core.config import get_settings
from src.core.security import encode_jwt_token
from src.presentation.http.access_control.dependencies import get_auth_use_case

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
REFRESH_VERSION = 7


def _session() -> AuthSession:
    return AuthSession(
        user_id=USER_ID,
        username="admin",
        role_key="developer",
        role_name="Developer",
        first_name="Ada",
        last_name="Lovelace",
        patronymic=None,
        refresh_token_version=REFRESH_VERSION,
        permissions=[],
    )


class FakeAuthUseCase:
    async def authenticate(self, username: str, password: str) -> AuthSession:
        return _session()

    async def session_for_user(self, user_id: UUID) -> AuthSession:
        return _session()


def _client(monkeypatch: MonkeyPatch) -> TestClient:
    monkeypatch.setenv("APP_DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
    monkeypatch.setenv("APP_JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("APP_ACCESS_TOKEN_TTL_SECONDS", "1800")
    monkeypatch.setenv("APP_REFRESH_TOKEN_TTL_SECONDS", "86400")
    monkeypatch.setenv("APP_REFRESH_TOKEN_REMEMBER_TTL_SECONDS", "2592000")
    monkeypatch.setenv("APP_AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("APP_AUTH_COOKIE_DOMAIN", "localhost")
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_auth_use_case] = lambda: FakeAuthUseCase()
    return TestClient(app)


def _refresh_cookie_max_age(response: object) -> int:
    for header in response.headers.get_list("set-cookie"):  # type: ignore[attr-defined]
        if header.startswith("refresh_cookie="):
            for part in header.split(";"):
                key, _, value = part.strip().partition("=")
                if key.lower() == "max-age":
                    return int(value)
    raise AssertionError("refresh_cookie Max-Age not found")


def _mint_refresh_cookie(refresh_version: int = REFRESH_VERSION) -> str:
    settings = get_settings()
    token, _ = encode_jwt_token(
        subject=USER_ID,
        token_type="refresh",
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_delta=timedelta(seconds=settings.refresh_token_ttl_seconds),
        additional_claims={"rv": refresh_version},
    )
    return token


def test_login_without_remember_uses_short_refresh_window(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "secret", "remember_me": False},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["data"]["user"]["username"] == "admin"
        assert payload["meta"]["operation"] == "auth.login"
        # 1 day (default) refresh window.
        assert _refresh_cookie_max_age(response) == 86400
    finally:
        get_settings.cache_clear()


def test_login_with_remember_issues_long_refresh_cookie(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "secret", "remember_me": True},
        )

        # 30 day refresh window with "remember me".
        assert _refresh_cookie_max_age(response) == 2592000
    finally:
        get_settings.cache_clear()


def test_refresh_with_valid_cookie_reissues_access(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Cookie": f"refresh_cookie={_mint_refresh_cookie()}"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["meta"]["operation"] == "auth.refresh"
        assert payload["data"]["user"]["id"] == str(USER_ID)
        # A fresh access cookie is issued on refresh.
        assert any(
            header.startswith("access_cookie=")
            for header in response.headers.get_list("set-cookie")
        )
    finally:
        get_settings.cache_clear()


def test_refresh_without_cookie_returns_401(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post("/api/v1/auth/refresh")

        assert response.status_code == 401
    finally:
        get_settings.cache_clear()


def test_refresh_with_revoked_version_returns_401(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)
        stale = _mint_refresh_cookie(refresh_version=REFRESH_VERSION + 1)

        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Cookie": f"refresh_cookie={stale}"},
        )

        assert response.status_code == 401
    finally:
        get_settings.cache_clear()
