from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from src.contexts.access_control.application.use_cases._shared import serialize_permission
from src.contexts.access_control.infrastructure.repositories import (
    RolePermissionRepository,
    RoleRepository,
)
from src.core.responses import ResponseMeta, SingleResponse


class RolePermissionSetUseCase:
    """Manage the full permission set attached to a role."""

    def __init__(
        self,
        *,
        roles: RoleRepository,
        role_permissions: RolePermissionRepository,
    ) -> None:
        self.roles = roles
        self.role_permissions = role_permissions

    async def read(self, role_id: UUID) -> SingleResponse[dict[str, object]]:
        await self.roles.read(role_id)
        rows = await self.role_permissions.list_for_role(role_id)
        return SingleResponse(
            data={
                "permissions": [
                    serialize_permission(permission, role_permission.scope)
                    for role_permission, permission in rows
                ],
            },
            meta=ResponseMeta(operation="roles.permissions.read"),
        )

    async def replace(
        self,
        role_id: UUID,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        await self.roles.read(role_id)
        rows = await self.role_permissions.replace_for_role(
            role_id,
            [item.model_dump(mode="python") for item in payload.permissions],
        )
        return SingleResponse(
            data={
                "permissions": [
                    serialize_permission(permission, role_permission.scope)
                    for role_permission, permission in rows
                ],
            },
            meta=ResponseMeta(operation="roles.permissions.replace"),
        )
