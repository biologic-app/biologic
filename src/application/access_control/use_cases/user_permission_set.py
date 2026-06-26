from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from src.application.access_control.use_cases._shared import (
    permission_sort_key,
    serialize_override,
    serialize_permission,
)
from src.core.responses import ResponseMeta, SingleResponse
from src.domain.uow import UnitOfWorkFactory


class _OverrideSetPayload(Protocol):
    overrides: list[Any]


class UserPermissionSetUseCase:
    """Read a user's effective permissions and manage per-user overrides."""

    def __init__(self, *, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def read_effective(self, user_id: UUID) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            user = await uow.users.read(user_id)
            role_rows = await uow.role_permissions.list_for_role(user.role_id)
            override_rows = await uow.user_permission_overrides.list_for_user(user_id)
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
        async with self._uow_factory() as uow:
            await uow.users.read(user_id)
            rows = await uow.user_permission_overrides.list_for_user(user_id)
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
        payload: _OverrideSetPayload,
    ) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            await uow.users.read(user_id)
            rows = await uow.user_permission_overrides.replace_for_user(
                user_id,
                [item.model_dump(mode="python") for item in payload.overrides],
            )
            await uow.commit()
            return SingleResponse(
                data={
                    "overrides": [
                        serialize_override(override, permission) for override, permission in rows
                    ],
                },
                meta=ResponseMeta(operation="users.overrides.replace"),
            )
