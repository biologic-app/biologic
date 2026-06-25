from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from src.contexts.catalogs.application.use_cases._shared import (
    list_response,
    payload_dict,
    single_response,
)
from src.contexts.catalogs.infrastructure.repositories import ConclusionRepository
from src.core.pagination import PaginationParams
from src.core.responses import ListResponse, SingleResponse

_FIELDS = (
    "id",
    "code",
    "name",
    "text_singular",
    "text_plural",
    "comment",
    "created_at",
    "updated_at",
)
_INCLUDES: tuple[str, ...] = ()


class ConclusionCrudUseCase:
    def __init__(self, *, repository: ConclusionRepository) -> None:
        self.repository = repository

    async def list(self, params: PaginationParams) -> ListResponse[dict[str, object]]:
        return list_response(await self.repository.list(params), params, _FIELDS, _INCLUDES)

    async def read(self, item_id: UUID) -> SingleResponse[dict[str, object]]:
        return single_response(await self.repository.read(item_id), _FIELDS)

    async def create(self, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        row = await self.repository.create(payload_dict(payload))
        return single_response(row, _FIELDS, operation="conclusions.create")

    async def update(self, item_id: UUID, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        row = await self.repository.update(item_id, payload_dict(payload))
        return single_response(row, _FIELDS, operation="conclusions.update")

    async def delete(self, item_id: UUID) -> None:
        await self.repository.delete(item_id)
