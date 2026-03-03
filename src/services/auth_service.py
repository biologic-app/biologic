from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import ClassVar

from src.core.config import Settings
from src.core.errors import NotFoundError, UnauthorizedError
from src.core.security import (
    TokenType,
    decode_jwt_token,
    encode_jwt_token,
    is_jwt_error,
    token_expiration,
    token_refresh_version,
    token_subject,
    verify_password,
)
from src.models.entities import Role, User
from src.repositories.auth_repository import AuthRepository
from src.schemas.auth import AuthLoginDTO, AuthPermissionDTO, AuthSessionDTO, AuthUserDTO


@dataclass(frozen=True, slots=True)
class AuthTokenBundle:
    access_token: str
    refresh_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime


class AuthService:
    _resource_map: ClassVar[dict[str, str]] = {
        "research_goals": "research-goals",
        "direction_statuses": "direction-statuses",
        "sample_statuses": "sample-statuses",
        "research_statuses": "research-statuses",
        "test_statuses": "test-statuses",
        "sample_types": "sample-types",
        "protocol_types": "protocol-types",
        "user_types": "user-types",
        "roles": "user-types",
        "permissions": "user-types",
        "user_scopes": "user-types",
        "role_permissions": "user-types",
    }
    _action_map: ClassVar[dict[str, str]] = {
        "read": "view",
        "update": "edit",
    }

    def __init__(self, repository: AuthRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings
        self._access_ttl = timedelta(minutes=settings.access_token_ttl_minutes)
        self._refresh_ttl = timedelta(days=settings.refresh_token_ttl_days)

    def _map_resource(self, resource: str) -> str:
        return self._resource_map.get(resource, resource.replace("_", "-"))

    def _map_action(self, action: str) -> str:
        return self._action_map.get(action, action)

    async def _build_permissions(self, role: Role) -> list[AuthPermissionDTO]:
        raw_permissions = await self._repository.list_permissions_by_role_id(role.id)
        normalized: dict[tuple[str, str], AuthPermissionDTO] = {
            ("dashboard", "view"): AuthPermissionDTO(resource="dashboard", action="view")
        }
        for resource, action in raw_permissions:
            mapped = AuthPermissionDTO(
                resource=self._map_resource(resource),
                action=self._map_action(action),
            )
            normalized[(mapped.resource, mapped.action)] = mapped
        return list(normalized.values())

    def _decode_token(self, token: str, token_type: TokenType) -> dict[str, object]:
        try:
            return decode_jwt_token(
                token,
                secret_key=self._settings.jwt_secret_key,
                algorithm=self._settings.jwt_algorithm,
                expected_type=token_type,
            )
        except Exception as exc:  # pragma: no cover - exact library errors vary
            if is_jwt_error(exc) or isinstance(exc, ValueError):
                raise UnauthorizedError("Invalid or expired token.") from exc
            raise

    def _build_user_dto(self, user: User, role: Role | None) -> AuthUserDTO:
        if role is None:
            raise NotFoundError(f"Role {user.role_id} was not found.")
        return AuthUserDTO(
            id=user.id,
            username=user.username,
            role_id=user.role_id,
            role_key=role.key,
            role_name=role.name,
            first_name=user.first_name,
            last_name=user.last_name,
            patronymic=user.patronymic,
        )

    def _build_session(
        self,
        user: User,
        role: Role | None,
        *,
        permissions: list[AuthPermissionDTO],
        access_expires_at: datetime,
        refresh_expires_at: datetime | None = None,
    ) -> AuthSessionDTO:
        return AuthSessionDTO(
            user=self._build_user_dto(user, role),
            permissions=permissions,
            access_expires_at=access_expires_at,
            refresh_expires_at=refresh_expires_at,
        )

    def _issue_tokens(self, user: User, role: Role) -> AuthTokenBundle:
        access_token, access_expires_at = encode_jwt_token(
            subject=user.id,
            token_type="access",
            secret_key=self._settings.jwt_secret_key,
            algorithm=self._settings.jwt_algorithm,
            expires_delta=self._access_ttl,
            additional_claims={"rk": role.key},
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
        auth_row = await self._repository.get_user_with_role_by_username(payload.username)
        if auth_row is None:
            raise UnauthorizedError("Invalid username or password.")

        user, role = auth_row
        if not verify_password(payload.password, user.password_hash):
            raise UnauthorizedError("Invalid username or password.")
        if role is None:
            raise NotFoundError(f"Role {user.role_id} was not found.")
        permissions = await self._build_permissions(role)

        tokens = self._issue_tokens(user, role)
        session = self._build_session(
            user,
            role,
            permissions=permissions,
            access_expires_at=tokens.access_expires_at,
            refresh_expires_at=tokens.refresh_expires_at,
        )
        return session, tokens

    async def me(self, access_token: str, refresh_token: str | None) -> AuthSessionDTO:
        access_payload = self._decode_token(access_token, "access")
        user_id = token_subject(access_payload)
        auth_row = await self._repository.get_user_with_role_by_id(user_id)
        if auth_row is None:
            raise NotFoundError(f"User {user_id} was not found.")
        user, role = auth_row
        if role is None:
            raise NotFoundError(f"Role {user.role_id} was not found.")
        permissions = await self._build_permissions(role)

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
            role,
            permissions=permissions,
            access_expires_at=token_expiration(access_payload),
            refresh_expires_at=refresh_expires_at,
        )

    async def refresh(self, refresh_token: str) -> tuple[AuthSessionDTO, AuthTokenBundle]:
        refresh_payload = self._decode_token(refresh_token, "refresh")
        user_id = token_subject(refresh_payload)
        refresh_version = token_refresh_version(refresh_payload)

        auth_row = await self._repository.get_user_with_role_by_id(user_id)
        if auth_row is None:
            raise NotFoundError(f"User {user_id} was not found.")
        user, role = auth_row
        if role is None:
            raise NotFoundError(f"Role {user.role_id} was not found.")
        permissions = await self._build_permissions(role)
        if user.refresh_token_version != refresh_version:
            raise UnauthorizedError("Refresh token is revoked.")

        next_version = await self._repository.bump_refresh_token_version(user.id)
        if next_version is None:
            raise NotFoundError(f"User {user.id} was not found.")
        user.refresh_token_version = next_version

        tokens = self._issue_tokens(user, role)
        session = self._build_session(
            user,
            role,
            permissions=permissions,
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

        auth_row = await self._repository.get_user_with_role_by_id(user_id)
        if auth_row is None:
            return
        user, _ = auth_row
        if user.refresh_token_version != refresh_version:
            return

        await self._repository.bump_refresh_token_version(user.id)
