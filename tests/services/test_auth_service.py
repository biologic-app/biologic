from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.core.config import Settings
from src.core.errors import NotFoundError, UnauthorizedError
from src.core.security import encode_jwt_token, hash_password
from src.models.entities import Role, User
from src.schemas.auth import AuthLoginDTO
from src.services.auth_service import AuthService


def _settings() -> Settings:
    return Settings(jwt_secret_key="test-secret")


def _build_user_role(*, password: str = "admin123", refresh_version: int = 0) -> tuple[User, Role]:
    role_id = uuid4()
    user = User(
        username="admin",
        password_hash=hash_password(password),
        role_id=role_id,
    )
    user.id = uuid4()
    user.refresh_token_version = refresh_version
    user.first_name = "System"
    user.last_name = "Administrator"

    role = Role(key="admin", name="Administrator")
    role.id = role_id
    return user, role


async def test_auth_service_login_success() -> None:
    user, role = _build_user_role()
    repository = SimpleNamespace(
        get_user_with_role_by_username=AsyncMock(return_value=(user, role)),
        list_permissions_by_role_id=AsyncMock(return_value=[("objects", "read"), ("objects", "update")]),
    )
    service = AuthService(repository=repository, settings=_settings())

    session, tokens = await service.login(AuthLoginDTO(username="admin", password="admin123"))

    assert session.user.username == "admin"
    assert session.user.role_key == "admin"
    assert any(perm.resource == "dashboard" and perm.action == "view" for perm in session.permissions)
    assert any(perm.resource == "objects" and perm.action == "view" for perm in session.permissions)
    assert any(perm.resource == "objects" and perm.action == "edit" for perm in session.permissions)
    assert tokens.access_token
    assert tokens.refresh_token


async def test_auth_service_login_invalid_credentials() -> None:
    user, role = _build_user_role(password="another")
    repository = SimpleNamespace(
        get_user_with_role_by_username=AsyncMock(return_value=(user, role)),
        list_permissions_by_role_id=AsyncMock(return_value=[]),
    )
    service = AuthService(repository=repository, settings=_settings())

    with pytest.raises(UnauthorizedError):
        await service.login(AuthLoginDTO(username="admin", password="admin123"))


async def test_auth_service_login_missing_role() -> None:
    user, _ = _build_user_role()
    repository = SimpleNamespace(
        get_user_with_role_by_username=AsyncMock(return_value=(user, None)),
        list_permissions_by_role_id=AsyncMock(return_value=[]),
    )
    service = AuthService(repository=repository, settings=_settings())

    with pytest.raises(NotFoundError):
        await service.login(AuthLoginDTO(username="admin", password="admin123"))


async def test_auth_service_me_reads_access_and_refresh_exp() -> None:
    settings = _settings()
    user, role = _build_user_role()
    access_token, _ = encode_jwt_token(
        subject=user.id,
        token_type="access",
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_delta=timedelta(minutes=15),
        additional_claims={"rk": role.key},
    )
    refresh_token, _ = encode_jwt_token(
        subject=user.id,
        token_type="refresh",
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_delta=timedelta(days=30),
        additional_claims={"rv": user.refresh_token_version},
    )
    repository = SimpleNamespace(
        get_user_with_role_by_id=AsyncMock(return_value=(user, role)),
        list_permissions_by_role_id=AsyncMock(return_value=[("objects", "read")]),
    )
    service = AuthService(repository=repository, settings=settings)

    session = await service.me(access_token, refresh_token)

    assert session.user.id == user.id
    assert session.refresh_expires_at is not None


async def test_auth_service_refresh_rotates_refresh_version() -> None:
    settings = _settings()
    user, role = _build_user_role(refresh_version=0)
    refresh_token, _ = encode_jwt_token(
        subject=user.id,
        token_type="refresh",
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_delta=timedelta(days=30),
        additional_claims={"rv": 0},
    )
    repository = SimpleNamespace(
        get_user_with_role_by_id=AsyncMock(return_value=(user, role)),
        bump_refresh_token_version=AsyncMock(return_value=1),
        list_permissions_by_role_id=AsyncMock(return_value=[("objects", "read")]),
    )
    service = AuthService(repository=repository, settings=settings)

    session, _ = await service.refresh(refresh_token)

    assert session.user.username == "admin"
    assert user.refresh_token_version == 1
    repository.bump_refresh_token_version.assert_awaited_once_with(user.id)


async def test_auth_service_refresh_rejects_revoked_token() -> None:
    settings = _settings()
    user, role = _build_user_role(refresh_version=5)
    refresh_token, _ = encode_jwt_token(
        subject=user.id,
        token_type="refresh",
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_delta=timedelta(days=30),
        additional_claims={"rv": 4},
    )
    repository = SimpleNamespace(
        get_user_with_role_by_id=AsyncMock(return_value=(user, role)),
        bump_refresh_token_version=AsyncMock(return_value=6),
        list_permissions_by_role_id=AsyncMock(return_value=[("objects", "read")]),
    )
    service = AuthService(repository=repository, settings=settings)

    with pytest.raises(UnauthorizedError):
        await service.refresh(refresh_token)


async def test_auth_service_logout_ignores_invalid_token() -> None:
    repository = SimpleNamespace(
        get_user_with_role_by_id=AsyncMock(),
        bump_refresh_token_version=AsyncMock(),
    )
    service = AuthService(repository=repository, settings=_settings())

    await service.logout("broken-token")

    repository.get_user_with_role_by_id.assert_not_called()
    repository.bump_refresh_token_version.assert_not_called()


async def test_auth_service_logout_revokes_valid_refresh() -> None:
    settings = _settings()
    user, role = _build_user_role(refresh_version=2)
    refresh_token, _ = encode_jwt_token(
        subject=user.id,
        token_type="refresh",
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_delta=timedelta(days=30),
        additional_claims={"rv": 2},
    )
    repository = SimpleNamespace(
        get_user_with_role_by_id=AsyncMock(return_value=(user, role)),
        bump_refresh_token_version=AsyncMock(return_value=3),
        list_permissions_by_role_id=AsyncMock(return_value=[("objects", "read")]),
    )
    service = AuthService(repository=repository, settings=settings)

    await service.logout(refresh_token)

    repository.bump_refresh_token_version.assert_awaited_once_with(user.id)
