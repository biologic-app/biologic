from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.application.access_control.use_cases._shared import (
    permission_sort_key,
    serialize_permission,
)
from src.core.errors import UnauthorizedError
from src.core.security import verify_password
from src.domain.uow import UnitOfWork, UnitOfWorkFactory


@dataclass(frozen=True)
class AuthSession:
    """Session data used by the router to build the response and tokens."""

    user_id: UUID
    username: str
    role_key: str
    role_name: str
    first_name: str | None
    last_name: str | None
    patronymic: str | None
    refresh_token_version: int
    permissions: list[dict[str, object]]


class AuthUseCase:
    """Authenticates by username/password and builds a session by user id."""

    def __init__(self, *, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def authenticate(self, username: str, password: str) -> AuthSession:
        async with self._uow_factory() as uow:
            user = await uow.users.get_by_username(username)
            if user is None or not verify_password(password, user.password_hash):
                raise UnauthorizedError("Invalid username or password.")
            return await self._build_session(uow, user)

    async def session_for_user(self, user_id: UUID) -> AuthSession:
        async with self._uow_factory() as uow:
            user = await uow.users.read(user_id)
            return await self._build_session(uow, user)

    async def _build_session(self, uow: UnitOfWork, user: Any) -> AuthSession:
        role = await uow.roles.read(user.role_id)
        role_rows = await uow.role_permissions.list_for_role(user.role_id)
        override_rows = await uow.user_permission_overrides.list_for_user(user.id)

        effective: dict[object, dict[str, object]] = {
            permission.id: serialize_permission(permission, role_permission.scope)
            for role_permission, permission in role_rows
        }
        for override, permission in override_rows:
            if override.allowed:
                effective[permission.id] = serialize_permission(permission, override.scope)
            else:
                effective.pop(permission.id, None)

        return AuthSession(
            user_id=user.id,
            username=user.username,
            role_key=role.key,
            role_name=role.name,
            first_name=user.first_name,
            last_name=user.last_name,
            patronymic=user.patronymic,
            refresh_token_version=user.refresh_token_version,
            permissions=sorted(effective.values(), key=permission_sort_key),
        )
