from uuid import UUID

from fastapi import Header

from src.application.access_control.use_cases.permission_crud import PermissionCrudUseCase
from src.application.access_control.use_cases.role_crud import RoleCrudUseCase
from src.application.access_control.use_cases.role_permission_crud import (
    RolePermissionCrudUseCase,
)
from src.application.access_control.use_cases.role_permission_set import (
    RolePermissionSetUseCase,
)
from src.application.access_control.use_cases.user_crud import UserCrudUseCase
from src.application.access_control.use_cases.user_permission_set import (
    UserPermissionSetUseCase,
)
from src.application.access_control.use_cases.user_scope_crud import UserScopeCrudUseCase
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


async def get_user_scope_use_case() -> UserScopeCrudUseCase:
    return UserScopeCrudUseCase(uow_factory=build_uow_factory())


async def get_role_permission_set_use_case() -> RolePermissionSetUseCase:
    return RolePermissionSetUseCase(uow_factory=build_uow_factory())


async def get_user_permission_set_use_case() -> UserPermissionSetUseCase:
    return UserPermissionSetUseCase(uow_factory=build_uow_factory())
