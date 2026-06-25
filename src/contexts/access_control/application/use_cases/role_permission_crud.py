from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from src.contexts.access_control.application.use_cases._shared import (
    list_response,
    payload_dict,
    single_response,
)
from src.contexts.access_control.infrastructure.repositories import RolePermissionRepository
from src.core.pagination import PaginationParams
from src.core.responses import ListResponse, SingleResponse

_FIELDS = ("id", "role_id", "permission_id", "scope")


class RolePermissionCrudUseCase:
    def __init__(self, *, repository: RolePermissionRepository) -> None:
        self.repository = repository

    async def list(self, params: PaginationParams) -> ListResponse[dict[str, object]]:
        return list_response(await self.repository.list(params), params, _FIELDS)

    async def read(self, item_id: UUID) -> SingleResponse[dict[str, object]]:
        return single_response(await self.repository.read(item_id), _FIELDS)

    async def create(self, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        row = await self.repository.create(payload_dict(payload))
        return single_response(row, _FIELDS, operation="role_permissions.create")

    async def update(self, item_id: UUID, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        row = await self.repository.update(item_id, payload_dict(payload))
        return single_response(row, _FIELDS, operation="role_permissions.update")

    async def delete(self, item_id: UUID) -> None:
        await self.repository.delete(item_id)
