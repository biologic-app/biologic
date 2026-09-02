from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy import select

from src.application.access_control.permission_registry import is_registered
from src.application.access_control.use_cases.auth import AuthUseCase
from src.application.access_control.use_cases.permission_crud import PermissionCrudUseCase
from src.application.access_control.use_cases.role_crud import RoleCrudUseCase
from src.application.access_control.use_cases.role_permission_crud import (
    RolePermissionCrudUseCase,
)
from src.application.access_control.use_cases.role_permission_set import (
    RolePermissionSetUseCase,
)
from src.application.access_control.use_cases.role_subscription_rule_crud import (
    RoleSubscriptionRuleCrudUseCase,
)
from src.application.access_control.use_cases.user_crud import UserCrudUseCase
from src.application.access_control.use_cases.user_permission_set import (
    UserPermissionSetUseCase,
)
from src.application.access_control.use_cases.user_scope_crud import UserScopeCrudUseCase
from src.core.branch_context import set_current_branch_id
from src.core.config import get_settings
from src.core.errors import ForbiddenError, UnauthorizedError
from src.core.security import (
    decode_jwt_token,
    token_jti,
    token_session_id,
    token_subject,
    token_version,
)
from src.infrastructure.db.models import (
    Permission,
    Role,
    RolePermission,
    Session,
    User,
    UserPermissionOverride,
    UserScope,
)
from src.infrastructure.uow import build_uow_factory


async def get_user_use_case() -> UserCrudUseCase:
    return UserCrudUseCase(uow_factory=build_uow_factory())


async def get_role_use_case() -> RoleCrudUseCase:
    return RoleCrudUseCase(uow_factory=build_uow_factory())


async def get_permission_use_case() -> PermissionCrudUseCase:
    return PermissionCrudUseCase(uow_factory=build_uow_factory())


async def get_role_permission_use_case() -> RolePermissionCrudUseCase:
    return RolePermissionCrudUseCase(uow_factory=build_uow_factory())


async def get_role_subscription_rule_use_case() -> RoleSubscriptionRuleCrudUseCase:
    return RoleSubscriptionRuleCrudUseCase(uow_factory=build_uow_factory())


async def get_user_scope_use_case() -> UserScopeCrudUseCase:
    return UserScopeCrudUseCase(uow_factory=build_uow_factory())


async def get_role_permission_set_use_case() -> RolePermissionSetUseCase:
    return RolePermissionSetUseCase(uow_factory=build_uow_factory())


async def get_user_permission_set_use_case() -> UserPermissionSetUseCase:
    return UserPermissionSetUseCase(uow_factory=build_uow_factory())


async def get_auth_use_case() -> AuthUseCase:
    return AuthUseCase(uow_factory=build_uow_factory())


async def get_current_user_id(request: Request) -> UUID:
    return (await get_current_principal(request)).user_id


@dataclass(frozen=True)
class CurrentPrincipal:
    user_id: UUID
    session_id: UUID
    token_version: int
    role_key: str
    is_superadmin: bool
    grants: frozenset[str]
    scopes: tuple[dict[str, object], ...]
    branch_id: UUID | None

    def can(self, code: str) -> bool:
        if self.is_superadmin or code in self.grants or "*" in self.grants:
            return True
        resource = code.split(".", maxsplit=1)[0]
        return f"{resource}.*" in self.grants


async def get_current_principal(request: Request) -> CurrentPrincipal:
    settings = get_settings()
    token = request.cookies.get(settings.access_cookie_name)
    if not token:
        raise UnauthorizedError("Missing access token.")
    try:
        payload = decode_jwt_token(
            token,
            secret_key=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
            expected_type="access",
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )
        user_id, session_id = token_subject(payload), token_session_id(payload)
        version = token_version(payload)
        token_jti(payload)
    except Exception as exc:  # noqa: BLE001
        raise UnauthorizedError("Invalid or expired access token.") from exc

    async with build_uow_factory()() as uow:
        user = await uow.session.get(User, user_id)  # type: ignore[union-attr]
        session = await uow.session.get(Session, session_id)  # type: ignore[union-attr]
        if user is None or user.deleted_at is not None or user.status != "active":
            raise UnauthorizedError("User is not active.")
        if session is None or session.user_id != user_id or session.revoked_at is not None:
            raise UnauthorizedError("Session has been revoked.")
        if session.expires_at <= datetime.now(UTC):
            raise UnauthorizedError("Session has expired.")
        if version != user.token_version or version != session.token_version:
            raise UnauthorizedError("Token has been revoked.")
        role = await uow.session.get(Role, user.role_id)  # type: ignore[union-attr]
        if role is None:
            raise UnauthorizedError("User role is missing.")
        rows = (
            await uow.session.execute(
                select(RolePermission, Permission)
                .join(Permission, Permission.id == RolePermission.permission_id)
                .where(RolePermission.role_id == role.id)
            )
        ).all()  # type: ignore[union-attr]
        grants = {f"{p.resource}.{p.action}" for rp, p in rows}
        overrides = (
            await uow.session.execute(
                select(UserPermissionOverride, Permission)
                .join(Permission, Permission.id == UserPermissionOverride.permission_id)
                .where(UserPermissionOverride.user_id == user.id)
            )
        ).all()  # type: ignore[union-attr]
        for override, permission in overrides:
            code = f"{permission.resource}.{permission.action}"
            (grants.add if override.allowed else grants.discard)(code)
        set_current_branch_id(user.branch_id)
        scope_rows = (
            (await uow.session.execute(select(UserScope).where(UserScope.user_id == user.id)))
            .scalars()
            .all()
        )  # type: ignore[union-attr]
        return CurrentPrincipal(
            user.id,
            session.id,
            version,
            role.key,
            role.key == "superadmin",
            frozenset(grants),
            tuple({"scope_kind": s.scope_kind, "scope_id": str(s.scope_id)} for s in scope_rows),
            user.branch_id,
        )


def require_permission(code: str):
    if not is_registered(code):
        raise ValueError(f"Unknown permission code: {code}")

    async def dependency(
        principal: CurrentPrincipal = Depends(get_current_principal),
    ) -> CurrentPrincipal:
        if not principal.can(code):
            raise ForbiddenError(f"Permission required: {code}")
        return principal

    return dependency


async def get_current_user_id_optional(request: Request) -> UUID | None:
    """Best-effort variant for endpoints that must keep working when called
    without a session (e.g. directly against the API), but should record who
    the caller was whenever a valid one is available — see
    Direction.created_by, used to target workflow notifications at a
    specific user instead of broadcasting them.
    """
    try:
        return await get_current_user_id(request)
    except UnauthorizedError:
        return None
