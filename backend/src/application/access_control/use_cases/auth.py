from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select

from src.application.access_control.use_cases._shared import (
    permission_sort_key,
    serialize_permission,
)
from src.core.config import get_settings
from src.core.errors import UnauthorizedError
from src.core.security import verify_password
from src.domain.uow import UnitOfWork, UnitOfWorkFactory
from src.infrastructure.db.models import Session


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
    session_id: UUID = field(default_factory=uuid4)
    status: str = "active"

    @property
    def token_version(self) -> int:
        """Canonical name used by JWT claims (legacy field kept for clients)."""
        return self.refresh_token_version


class AuthUseCase:
    """Authenticates by username/password and builds a session by user id."""

    def __init__(self, *, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def authenticate(self, username: str, password: str) -> AuthSession:
        async with self._uow_factory() as uow:
            user = await uow.users.get_by_username(username)
            if (
                user is None
                or getattr(user, "deleted_at", None) is not None
                or getattr(user, "status", "active") != "active"
                or not verify_password(password, user.password_hash)
            ):
                raise UnauthorizedError("Invalid username or password.")
            session = await self._build_session(uow, user)
            if getattr(uow, "session", None) is not None:
                uow.session.add(
                    Session(
                        id=session.session_id,
                        user_id=user.id,
                        expires_at=datetime.now(UTC)
                        + timedelta(seconds=get_settings().refresh_token_remember_ttl_seconds),
                        token_version=int(
                            getattr(
                                user, "token_version", getattr(user, "refresh_token_version", 0)
                            )
                        ),
                    )
                )
                await uow.commit()
            return session

    async def session_for_user(self, user_id: UUID) -> AuthSession:
        async with self._uow_factory() as uow:
            user = await uow.users.read(user_id)
            if (
                getattr(user, "deleted_at", None) is not None
                or getattr(user, "status", "active") != "active"
            ):
                raise UnauthorizedError("User is not active.")
            session_id: UUID | None = None
            if getattr(uow, "session", None) is not None:
                row = (
                    await uow.session.execute(
                        select(Session)
                        .where(Session.user_id == user_id, Session.revoked_at.is_(None))
                        .order_by(Session.last_seen_at.desc())
                        .limit(1)
                    )
                ).scalar_one_or_none()  # type: ignore[union-attr]
                session_id = row.id if row is not None else None
            return await self._build_session(uow, user, session_id=session_id)

    async def _build_session(
        self, uow: UnitOfWork, user: Any, *, session_id: UUID | None = None
    ) -> AuthSession:
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
            refresh_token_version=int(
                getattr(user, "token_version", getattr(user, "refresh_token_version", 0))
            ),
            permissions=sorted(effective.values(), key=permission_sort_key),
            session_id=session_id or uuid4(),
            status=getattr(user, "status", "active"),
        )
