from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import Response
from starlette.requests import Request

from src.api.v1.endpoints.auth import auth_login, auth_logout, auth_me, auth_refresh
from src.core.config import Settings
from src.core.errors import UnauthorizedError
from src.schemas.auth import AuthLoginDTO, AuthSessionDTO, AuthUserDTO
from src.services.auth_service import AuthTokenBundle


def _settings() -> Settings:
    return Settings(jwt_secret_key="test-secret")


def _make_request(path: str, cookies: dict[str, str] | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if cookies:
        cookie_header = "; ".join(f"{key}={value}" for key, value in cookies.items())
        headers.append((b"cookie", cookie_header.encode()))
    scope = {
        "type": "http",
        "method": "POST",
        "path": path,
        "headers": headers,
        "query_string": b"",
    }
    return Request(scope)


def _session() -> AuthSessionDTO:
    return AuthSessionDTO(
        user=AuthUserDTO(
            id=uuid4(),
            username="admin",
            role_id=uuid4(),
            role_key="admin",
            role_name="Administrator",
            first_name="System",
            last_name="Administrator",
        ),
        access_expires_at=datetime.now(UTC),
        refresh_expires_at=datetime.now(UTC),
    )


def _tokens() -> AuthTokenBundle:
    now = datetime.now(UTC)
    return AuthTokenBundle(
        access_token="access-token",
        refresh_token="refresh-token",
        access_expires_at=now,
        refresh_expires_at=now,
    )


async def test_auth_login_sets_cookies_and_returns_session() -> None:
    service = SimpleNamespace(login=AsyncMock(return_value=(_session(), _tokens())))
    response = Response()
    settings = _settings()

    result = await auth_login(
        payload=AuthLoginDTO(username="admin", password="admin123"),
        response=response,
        service=service,
        settings=settings,
    )

    set_cookie_headers = [
        value.decode() for key, value in response.raw_headers if key == b"set-cookie"
    ]
    assert result.meta.operation == "login"
    assert any(settings.access_cookie_name in header for header in set_cookie_headers)
    assert any(settings.refresh_cookie_name in header for header in set_cookie_headers)


async def test_auth_me_requires_access_cookie() -> None:
    with pytest.raises(UnauthorizedError, match="Access token is missing"):
        await auth_me(
            request=_make_request("/api/v1/auth/me"),
            service=SimpleNamespace(me=AsyncMock()),
            settings=_settings(),
        )


async def test_auth_me_reads_tokens_from_cookies() -> None:
    service = SimpleNamespace(me=AsyncMock(return_value=_session()))
    settings = _settings()
    request = _make_request(
        "/api/v1/auth/me",
        {
            settings.access_cookie_name: "access-token",
            settings.refresh_cookie_name: "refresh-token",
        },
    )

    result = await auth_me(request=request, service=service, settings=settings)

    assert result.meta.operation == "me"
    service.me.assert_awaited_once_with("access-token", "refresh-token")


async def test_auth_refresh_requires_refresh_cookie() -> None:
    with pytest.raises(UnauthorizedError, match="Refresh token is missing"):
        await auth_refresh(
            request=_make_request("/api/v1/auth/refresh"),
            response=Response(),
            service=SimpleNamespace(refresh=AsyncMock()),
            settings=_settings(),
        )


async def test_auth_refresh_rotates_cookie_pair() -> None:
    service = SimpleNamespace(refresh=AsyncMock(return_value=(_session(), _tokens())))
    response = Response()
    settings = _settings()
    request = _make_request(
        "/api/v1/auth/refresh",
        {settings.refresh_cookie_name: "refresh-token"},
    )

    result = await auth_refresh(
        request=request,
        response=response,
        service=service,
        settings=settings,
    )

    set_cookie_headers = [
        value.decode() for key, value in response.raw_headers if key == b"set-cookie"
    ]
    assert result.meta.operation == "refresh"
    assert any(settings.access_cookie_name in header for header in set_cookie_headers)
    assert any(settings.refresh_cookie_name in header for header in set_cookie_headers)
    service.refresh.assert_awaited_once_with("refresh-token")


async def test_auth_logout_clears_cookies() -> None:
    service = SimpleNamespace(logout=AsyncMock(return_value=None))
    response = Response()
    settings = _settings()
    request = _make_request(
        "/api/v1/auth/logout",
        {settings.refresh_cookie_name: "refresh-token"},
    )

    result = await auth_logout(
        request=request,
        response=response,
        service=service,
        settings=settings,
    )

    set_cookie_headers = [
        value.decode() for key, value in response.raw_headers if key == b"set-cookie"
    ]
    assert result.meta.operation == "logout"
    assert len(set_cookie_headers) == 2
    service.logout.assert_awaited_once_with("refresh-token")
