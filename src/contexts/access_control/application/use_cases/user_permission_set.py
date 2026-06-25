from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from src.contexts.access_control.application.use_cases._shared import (
    permission_sort_key,
    serialize_override,
    serialize_permission,
)
from src.contexts.access_control.infrastructure.repositories import (
    RolePermissionRepository,
    UserPermissionOverrideRepository,
    UserRepository,
)
from src.core.responses import ResponseMeta, SingleResponse


class UserPermissionSetUseCase:
    """Read a user's effective permissions and manage per-user overrides."""

    def __init__(
        self,
        *,
        users: UserRepository,
        role_permissions: RolePermissionRepository,
        user_permission_overrides: UserPermissionOverrideRepository,
    ) -> None:
        self.users = users
        self.role_permissions = role_permissions
        self.user_permission_overrides = user_permission_overrides

    async def read_effective(self, user_id: UUID) -> SingleResponse[dict[str, object]]:
        user = await self.users.read(user_id)
        role_rows = await self.role_permissions.list_for_role(user.role_id)
        override_rows = await self.user_permission_overrides.list_for_user(user_id)
        effective = {
            permission.id: serialize_permission(permission, role_permission.scope)
            for role_permission, permission in role_rows
        }
        for override, permission in override_rows:
            if override.allowed:
                effective[permission.id] = serialize_permission(permission, override.scope)
            else:
                effective.pop(permission.id, None)
        return SingleResponse(
            data={"permissions": sorted(effective.values(), key=permission_sort_key)},
            meta=ResponseMeta(operation="users.permissions.read"),
        )

    async def read_overrides(self, user_id: UUID) -> SingleResponse[dict[str, object]]:
        await self.users.read(user_id)
        rows = await self.user_permission_overrides.list_for_user(user_id)
        return SingleResponse(
            data={
                "overrides": [
                    serialize_override(override, permission) for override, permission in rows
                ],
            },
            meta=ResponseMeta(operation="users.overrides.read"),
        )

    async def replace_overrides(
        self,
        user_id: UUID,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        await self.users.read(user_id)
        rows = await self.user_permission_overrides.replace_for_user(
            user_id,
            [item.model_dump(mode="python") for item in payload.overrides],
        )
        return SingleResponse(
            data={
                "overrides": [
                    serialize_override(override, permission) for override, permission in rows
                ],
            },
            meta=ResponseMeta(operation="users.overrides.replace"),
        )
