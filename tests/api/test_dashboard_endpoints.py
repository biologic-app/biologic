from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from starlette.requests import Request

from src.api.v1.endpoints.dashboard import (
    create_quick_action,
    delete_quick_action,
    list_quick_actions,
    update_quick_action,
)
from src.core.config import Settings
from src.core.errors import UnauthorizedError
from src.schemas.auth import AuthPermissionDTO, AuthSessionDTO, AuthUserDTO
from src.schemas.dashboard import DashboardQuickActionCreateDTO, DashboardQuickActionUpdateDTO
from src.services.dashboard_service import DashboardQuickActionsService


def _settings() -> Settings:
    return Settings(jwt_secret_key="test-secret")


def _make_request(path: str, cookies: dict[str, str] | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if cookies:
        cookie_header = "; ".join(f"{key}={value}" for key, value in cookies.items())
        headers.append((b"cookie", cookie_header.encode()))
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": headers,
        "query_string": b"",
    }
    return Request(scope)


def _session(role_key: str, permissions: list[tuple[str, str]]) -> AuthSessionDTO:
    return AuthSessionDTO(
        user=AuthUserDTO(
            id=uuid4(),
            username="demo",
            role_id=uuid4(),
            role_key=role_key,
            role_name=role_key,
            first_name="Demo",
            last_name="User",
        ),
        permissions=[
            AuthPermissionDTO(resource=resource, action=action)
            for resource, action in permissions
        ],
        access_expires_at=datetime.now(UTC),
        refresh_expires_at=datetime.now(UTC),
    )


async def test_dashboard_list_requires_access_cookie() -> None:
    with pytest.raises(UnauthorizedError, match="Access token is missing"):
        await list_quick_actions(
            request=_make_request("/api/v1/dashboard/quick-actions"),
            service=DashboardQuickActionsService(),
            auth_service=SimpleNamespace(me=AsyncMock()),
            settings=_settings(),
            offset=0,
            limit=50,
        )


async def test_dashboard_quick_actions_crud_flow() -> None:
    settings = _settings()
    session = _session(
        "admin",
        [("objects", "create"), ("objects", "view"), ("samples", "view"), ("users", "view")],
    )
    service = DashboardQuickActionsService()
    auth_service = SimpleNamespace(me=AsyncMock(return_value=session))
    request = _make_request(
        "/api/v1/dashboard/quick-actions",
        {
            settings.access_cookie_name: "access-token",
            settings.refresh_cookie_name: "refresh-token",
        },
    )

    listed = await list_quick_actions(
        request=request,
        service=service,
        auth_service=auth_service,
        settings=settings,
        offset=0,
        limit=50,
    )
    assert listed.meta.total >= 1

    created = await create_quick_action(
        payload=DashboardQuickActionCreateDTO(
            label="Создать объект",
            resource="objects",
            action="create",
            to="/objects#create",
            icon="pi pi-cog",
        ),
        request=request,
        service=service,
        auth_service=auth_service,
        settings=settings,
    )
    assert created.meta.operation == "create"

    updated = await update_quick_action(
        quick_action_id=created.data.id,
        payload=DashboardQuickActionUpdateDTO(
            label="Открыть объекты",
            action="view",
            to="/objects",
        ),
        request=request,
        service=service,
        auth_service=auth_service,
        settings=settings,
    )
    assert updated.meta.operation == "update"
    assert updated.data.label == "Открыть объекты"

    deleted = await delete_quick_action(
        quick_action_id=created.data.id,
        request=request,
        service=service,
        auth_service=auth_service,
        settings=settings,
    )
    assert deleted.ok is True
