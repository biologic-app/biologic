from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from src.application.catalogs.use_cases._shared import (
    list_response,
    payload_dict,
    single_response,
)
from src.core.pagination import PaginationParams
from src.core.responses import ListResponse, SingleResponse
from src.domain.uow import UnitOfWorkFactory
from src.infrastructure.repositories.catalogs import reject_status_write

_FIELDS = ("id", "code", "color", "created_at", "updated_at")


class DirectionStatusCrudUseCase:
    resource = "direction_statuses"

    def __init__(self, *, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def list(self, params: PaginationParams) -> ListResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            return list_response(await uow.direction_statuses.list(params), params, _FIELDS)

    async def read(self, item_id: UUID) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            return single_response(await uow.direction_statuses.read(item_id), _FIELDS)

    async def update(self, item_id: UUID, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            row = await uow.direction_statuses.update(item_id, payload_dict(payload))
            await uow.commit()
            return single_response(row, _FIELDS, operation="direction_statuses.update")

    def reject_write(self) -> None:
        reject_status_write(self.resource)
