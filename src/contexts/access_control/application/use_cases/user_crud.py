from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from src.contexts.access_control.application.use_cases._shared import (
    list_response,
    payload_dict,
    single_response,
)
from src.contexts.access_control.infrastructure.repositories import UserRepository
from src.core.pagination import PaginationParams
from src.core.responses import ListResponse, SingleResponse

_FIELDS = (
    "id",
    "username",
    "refresh_token_version",
    "code",
    "first_name",
    "last_name",
    "patronymic",
    "is_registrar",
    "is_lab_head",
    "is_branch_head",
    "role_id",
    "lab_id",
    "created_at",
    "updated_at",
)


class UserCrudUseCase:
    def __init__(self, *, repository: UserRepository) -> None:
        self.repository = repository

    async def list(self, params: PaginationParams) -> ListResponse[dict[str, object]]:
        return list_response(await self.repository.list(params), params, _FIELDS)

    async def read(self, item_id: UUID) -> SingleResponse[dict[str, object]]:
        return single_response(await self.repository.read(item_id), _FIELDS)

    async def create(self, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        row = await self.repository.create(payload_dict(payload))
        return single_response(row, _FIELDS, operation="users.create")

    async def update(self, item_id: UUID, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        row = await self.repository.update(item_id, payload_dict(payload))
        return single_response(row, _FIELDS, operation="users.update")

    async def delete(self, item_id: UUID) -> None:
        await self.repository.delete(item_id)
