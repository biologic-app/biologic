from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from src.contexts.catalogs.application.use_cases._shared import (
    list_response,
    payload_dict,
    single_response,
)
from src.contexts.catalogs.infrastructure.repositories import (
    ResearchStatusRepository,
    reject_status_write,
)
from src.core.pagination import PaginationParams
from src.core.responses import ListResponse, SingleResponse

_FIELDS = ("id", "code", "name", "created_at", "updated_at")


class ResearchStatusCrudUseCase:
    resource = "research_statuses"

    def __init__(self, *, repository: ResearchStatusRepository) -> None:
        self.repository = repository

    async def list(self, params: PaginationParams) -> ListResponse[dict[str, object]]:
        return list_response(await self.repository.list(params), params, _FIELDS)

    async def read(self, item_id: UUID) -> SingleResponse[dict[str, object]]:
        return single_response(await self.repository.read(item_id), _FIELDS)

    async def update(self, item_id: UUID, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        row = await self.repository.update(item_id, payload_dict(payload))
        return single_response(row, _FIELDS, operation="research_statuses.update")

    def reject_write(self) -> None:
        reject_status_write(self.resource)
