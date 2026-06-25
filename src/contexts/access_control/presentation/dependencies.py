from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.access_control.application.use_cases.permission_crud import PermissionCrudUseCase
from src.contexts.access_control.application.use_cases.role_crud import RoleCrudUseCase
from src.contexts.access_control.application.use_cases.role_permission_crud import (
    RolePermissionCrudUseCase,
)
from src.contexts.access_control.application.use_cases.role_permission_set import (
    RolePermissionSetUseCase,
)
from src.contexts.access_control.application.use_cases.user_crud import UserCrudUseCase
from src.contexts.access_control.application.use_cases.user_permission_set import (
    UserPermissionSetUseCase,
)
from src.contexts.access_control.application.use_cases.user_scope_crud import UserScopeCrudUseCase
from src.contexts.access_control.infrastructure.repositories import (
    PermissionRepository,
    RolePermissionRepository,
    RoleRepository,
    UserPermissionOverrideRepository,
    UserRepository,
    UserScopeRepository,
)
from src.core.database import get_db_session


async def get_actor_id(x_actor_id: UUID = Header(alias="X-Actor-Id")) -> UUID:
    return x_actor_id


async def get_user_use_case(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserCrudUseCase:
    return UserCrudUseCase(repository=UserRepository(session=session))


async def get_role_use_case(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RoleCrudUseCase:
    return RoleCrudUseCase(repository=RoleRepository(session=session))


async def get_permission_use_case(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PermissionCrudUseCase:
    return PermissionCrudUseCase(repository=PermissionRepository(session=session))


async def get_role_permission_use_case(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RolePermissionCrudUseCase:
    return RolePermissionCrudUseCase(repository=RolePermissionRepository(session=session))


async def get_user_scope_use_case(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserScopeCrudUseCase:
    return UserScopeCrudUseCase(repository=UserScopeRepository(session=session))


async def get_role_permission_set_use_case(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RolePermissionSetUseCase:
    return RolePermissionSetUseCase(
        roles=RoleRepository(session=session),
        role_permissions=RolePermissionRepository(session=session),
    )


async def get_user_permission_set_use_case(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserPermissionSetUseCase:
    return UserPermissionSetUseCase(
        users=UserRepository(session=session),
        role_permissions=RolePermissionRepository(session=session),
        user_permission_overrides=UserPermissionOverrideRepository(session=session),
    )
