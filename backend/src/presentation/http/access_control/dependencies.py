from uuid import UUID

from fastapi import Header, Request

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
from src.core.config import get_settings
from src.core.errors import UnauthorizedError
from src.core.security import decode_jwt_token, token_subject
from src.infrastructure.uow import build_uow_factory


async def get_actor_id(x_actor_id: UUID = Header(alias="X-Actor-Id")) -> UUID:
    return x_actor_id


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
        )
        return token_subject(payload)
    except Exception as exc:  # noqa: BLE001 — any decode failure is a 401
        raise UnauthorizedError("Invalid or expired access token.") from exc


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
