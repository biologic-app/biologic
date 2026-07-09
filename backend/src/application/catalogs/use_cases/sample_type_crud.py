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

_FIELDS = ("id", "code", "name", "created_at", "updated_at")
_INCLUDES: tuple[str, ...] = ()


class SampleTypeCrudUseCase:
    def __init__(self, *, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def list(self, params: PaginationParams) -> ListResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            return list_response(await uow.sample_types.list(params), params, _FIELDS, _INCLUDES)

    async def read(self, item_id: UUID) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            return single_response(await uow.sample_types.read(item_id), _FIELDS)

    async def create(self, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            row = await uow.sample_types.create(payload_dict(payload))
            await uow.commit()
            return single_response(row, _FIELDS, operation="sample_types.create")

    async def update(self, item_id: UUID, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            row = await uow.sample_types.update(item_id, payload_dict(payload))
            await uow.commit()
            return single_response(row, _FIELDS, operation="sample_types.update")

    async def delete(self, item_id: UUID) -> None:
        async with self._uow_factory() as uow:
            await uow.sample_types.delete(item_id)
            await uow.commit()
