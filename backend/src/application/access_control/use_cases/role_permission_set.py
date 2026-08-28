from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import update

from src.application.access_control.use_cases._shared import serialize_permission
from src.core.responses import ResponseMeta, SingleResponse
from src.domain.uow import UnitOfWorkFactory
from src.infrastructure.db.models import User


class _PermissionSetPayload(Protocol):
    permissions: list[Any]


class RolePermissionSetUseCase:
    """Manage the full permission set attached to a role."""

    def __init__(self, *, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def read(self, role_id: UUID) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            await uow.roles.read(role_id)
            rows = await uow.role_permissions.list_for_role(role_id)
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
        payload: _PermissionSetPayload,
    ) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            await uow.roles.read(role_id)
            rows = await uow.role_permissions.replace_for_role(
                role_id,
                [item.model_dump(mode="python") for item in payload.permissions],
            )
            if getattr(uow, "session", None) is not None:
                await uow.session.execute(
                    update(User)
                    .where(User.role_id == role_id)
                    .values(token_version=User.token_version + 1)
                )
            await uow.commit()
            return SingleResponse(
                data={
                    "permissions": [
                        serialize_permission(permission, role_permission.scope)
                        for role_permission, permission in rows
                    ],
                },
                meta=ResponseMeta(operation="roles.permissions.replace"),
            )
