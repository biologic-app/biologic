from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import ClassVar
from uuid import UUID, uuid5

from src.core.config import Settings
from src.core.errors import UnauthorizedError
from src.core.security import (
    TokenType,
    decode_jwt_token,
    encode_jwt_token,
    is_jwt_error,
    token_expiration,
    token_refresh_version,
    token_subject,
)
from src.schemas.auth import AuthLoginDTO, AuthPermissionDTO, AuthSessionDTO, AuthUserDTO
from src.services.auth_service import AuthTokenBundle


@dataclass(slots=True)
class MockAuthUser:
    id: UUID
    username: str
    password: str
    role_key: str
    role_name: str
    first_name: str | None
    last_name: str | None
    patronymic: str | None
    permissions: list[AuthPermissionDTO]
    refresh_token_version: int = 0


def _user_id(username: str) -> UUID:
    return uuid5(UUID("9f4dbf59-1f36-4fd3-b04f-9e3f5e28adf8"), f"mock-auth:{username}")


class MockAuthService:
    _all_resources: ClassVar[tuple[str, ...]] = (
        "dashboard",
        "directions",
        "direction-statuses",
        "samples",
        "sample-statuses",
        "research-statuses",
        "test-statuses",
        "protocols",
        "research",
        "conclusions",
        "tests",
        "doctors",
        "branches",
        "labs",
        "users",
        "research-goals",
        "sample-types",
        "indicators",
        "protocol-types",
        "user-types",
        "objects",
    )
    _crud_actions: ClassVar[tuple[str, ...]] = ("create", "edit", "delete")

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._access_ttl = timedelta(minutes=settings.access_token_ttl_minutes)
        self._refresh_ttl = timedelta(days=settings.refresh_token_ttl_days)
        self._users_by_id: dict[UUID, MockAuthUser] = {}
        self._users_by_username: dict[str, MockAuthUser] = {}
        self._init_users()

    def _init_users(self) -> None:
        admin_permissions = [
            *[
                AuthPermissionDTO(resource=resource, action="view")
                for resource in self._all_resources
            ],
            *[
                AuthPermissionDTO(resource=resource, action=action)
                for resource in self._all_resources
                if resource != "dashboard"
                for action in self._crud_actions
            ],
        ]
        doctor_permissions = [
            AuthPermissionDTO(resource="dashboard", action="view"),
            AuthPermissionDTO(resource="directions", action="view"),
            AuthPermissionDTO(resource="protocols", action="view"),
            AuthPermissionDTO(resource="research", action="view"),
            AuthPermissionDTO(resource="conclusions", action="view"),
            AuthPermissionDTO(resource="research-goals", action="view"),
        ]
        technician_permissions = [
            AuthPermissionDTO(resource="dashboard", action="view"),
            AuthPermissionDTO(resource="directions", action="view"),
            AuthPermissionDTO(resource="samples", action="view"),
            AuthPermissionDTO(resource="research", action="view"),
            AuthPermissionDTO(resource="sample-types", action="view"),
            AuthPermissionDTO(resource="indicators", action="view"),
        ]
        users = [
            MockAuthUser(
                id=_user_id("admin"),
                username="admin",
                password="admin123",
                role_key="admin",
                role_name="Administrator",
                first_name="System",
                last_name="Administrator",
                patronymic=None,
                permissions=admin_permissions,
            ),
            MockAuthUser(
                id=_user_id("doctor"),
                username="doctor",
                password="doctor123",
                role_key="doctor",
                role_name="Doctor",
                first_name="Demo",
                last_name="Doctor",
                patronymic=None,
                permissions=doctor_permissions,
            ),
            MockAuthUser(
                id=_user_id("tech"),
                username="tech",
                password="tech123",
                role_key="technician",
                role_name="Technician",
                first_name="Demo",
                last_name="Technician",
                patronymic=None,
                permissions=technician_permissions,
            ),
        ]
        self._users_by_id = {user.id: user for user in users}
        self._users_by_username = {user.username: user for user in users}

    def _decode_token(self, token: str, token_type: TokenType) -> dict[str, object]:
        try:
            return decode_jwt_token(
                token,
                secret_key=self._settings.jwt_secret_key,
                algorithm=self._settings.jwt_algorithm,
                expected_type=token_type,
            )
        except Exception as exc:
            if is_jwt_error(exc) or isinstance(exc, ValueError):
                raise UnauthorizedError("Invalid or expired token.") from exc
            raise

    def _build_user_dto(self, user: MockAuthUser) -> AuthUserDTO:
        return AuthUserDTO(
            id=user.id,
            username=user.username,
            role_id=user.id,
            role_key=user.role_key,
            role_name=user.role_name,
            first_name=user.first_name,
            last_name=user.last_name,
            patronymic=user.patronymic,
        )

    def _build_session(
        self,
        user: MockAuthUser,
        *,
        access_expires_at: datetime,
        refresh_expires_at: datetime | None = None,
    ) -> AuthSessionDTO:
        return AuthSessionDTO(
            user=self._build_user_dto(user),
            permissions=user.permissions,
            access_expires_at=access_expires_at,
            refresh_expires_at=refresh_expires_at,
        )

    def _issue_tokens(self, user: MockAuthUser) -> AuthTokenBundle:
        access_token, access_expires_at = encode_jwt_token(
            subject=user.id,
            token_type="access",
            secret_key=self._settings.jwt_secret_key,
            algorithm=self._settings.jwt_algorithm,
            expires_delta=self._access_ttl,
            additional_claims={"rk": user.role_key},
        )
        refresh_token, refresh_expires_at = encode_jwt_token(
            subject=user.id,
            token_type="refresh",
            secret_key=self._settings.jwt_secret_key,
            algorithm=self._settings.jwt_algorithm,
            expires_delta=self._refresh_ttl,
            additional_claims={"rv": user.refresh_token_version},
        )
        return AuthTokenBundle(
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires_at=access_expires_at,
            refresh_expires_at=refresh_expires_at,
        )

    async def login(self, payload: AuthLoginDTO) -> tuple[AuthSessionDTO, AuthTokenBundle]:
        user = self._users_by_username.get(payload.username)
        if user is None or payload.password != user.password:
            raise UnauthorizedError("Invalid username or password.")
        tokens = self._issue_tokens(user)
        session = self._build_session(
            user,
            access_expires_at=tokens.access_expires_at,
            refresh_expires_at=tokens.refresh_expires_at,
        )
        return session, tokens

    async def me(self, access_token: str, refresh_token: str | None) -> AuthSessionDTO:
        access_payload = self._decode_token(access_token, "access")
        user_id = token_subject(access_payload)
        user = self._users_by_id.get(user_id)
        if user is None:
            raise UnauthorizedError("User is not available.")
        refresh_expires_at = None
        if refresh_token:
            try:
                refresh_payload = self._decode_token(refresh_token, "refresh")
                if token_subject(refresh_payload) == user.id:
                    refresh_expires_at = token_expiration(refresh_payload)
            except UnauthorizedError:
                refresh_expires_at = None
        return self._build_session(
            user,
            access_expires_at=token_expiration(access_payload),
            refresh_expires_at=refresh_expires_at,
        )

    async def refresh(self, refresh_token: str) -> tuple[AuthSessionDTO, AuthTokenBundle]:
        refresh_payload = self._decode_token(refresh_token, "refresh")
        user_id = token_subject(refresh_payload)
        refresh_version = token_refresh_version(refresh_payload)
        user = self._users_by_id.get(user_id)
        if user is None:
            raise UnauthorizedError("User is not available.")
        if user.refresh_token_version != refresh_version:
            raise UnauthorizedError("Refresh token is revoked.")
        user.refresh_token_version += 1
        tokens = self._issue_tokens(user)
        session = self._build_session(
            user,
            access_expires_at=tokens.access_expires_at,
            refresh_expires_at=tokens.refresh_expires_at,
        )
        return session, tokens

    async def logout(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        try:
            refresh_payload = self._decode_token(refresh_token, "refresh")
            user_id = token_subject(refresh_payload)
            refresh_version = token_refresh_version(refresh_payload)
        except UnauthorizedError:
            return
        user = self._users_by_id.get(user_id)
        if user is None:
            return
        if user.refresh_token_version != refresh_version:
            return
        user.refresh_token_version += 1
