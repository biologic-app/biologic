from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.access_control.application.crud import AccessControlCrudUseCase
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


async def get_access_control_use_case(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AccessControlCrudUseCase:
    return AccessControlCrudUseCase(
        users=UserRepository(session=session),
        roles=RoleRepository(session=session),
        permissions=PermissionRepository(session=session),
        role_permissions=RolePermissionRepository(session=session),
        user_permission_overrides=UserPermissionOverrideRepository(session=session),
        user_scopes=UserScopeRepository(session=session),
    )
