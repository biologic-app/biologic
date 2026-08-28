from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from src.application.access_control.use_cases._shared import (
    list_response,
    payload_dict,
    single_response,
)
from src.core.errors import ForbiddenError
from src.core.pagination import PaginationParams
from src.core.responses import ListResponse, SingleResponse
from src.domain.uow import UnitOfWorkFactory

_FIELDS = ("id", "key", "name", "scope_type", "is_system", "created_at", "updated_at")


class RoleCrudUseCase:
    def __init__(self, *, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def list(self, params: PaginationParams) -> ListResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            return list_response(await uow.roles.list(params), params, _FIELDS)

    async def read(self, item_id: UUID) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            return single_response(await uow.roles.read(item_id), _FIELDS)

    async def create(self, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        if payload.model_dump(exclude_unset=True).get("key") == "superadmin":
            raise ForbiddenError("The superadmin role is managed directly in the database.")
        async with self._uow_factory() as uow:
            row = await uow.roles.create(payload_dict(payload))
            await uow.commit()
            return single_response(row, _FIELDS, operation="roles.create")

    async def update(self, item_id: UUID, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            current = await uow.roles.read(item_id)
            if getattr(current, "is_system", False):
                raise ForbiddenError("System roles cannot be modified through the API.")
            if payload.model_dump(exclude_unset=True).get("key") == "superadmin":
                raise ForbiddenError("The superadmin role is managed directly in the database.")
            row = await uow.roles.update(item_id, payload_dict(payload))
            await uow.commit()
            return single_response(row, _FIELDS, operation="roles.update")

    async def delete(self, item_id: UUID) -> None:
        async with self._uow_factory() as uow:
            current = await uow.roles.read(item_id)
            is_system = getattr(current, "is_system", False)
            is_superadmin = getattr(current, "key", None) == "superadmin"
            if is_system or is_superadmin:
                raise ForbiddenError("System roles cannot be deleted through the API.")
            await uow.roles.delete(item_id)
            await uow.commit()
