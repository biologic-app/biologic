from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel

from src.application.access_control.use_cases._shared import (
    list_response,
    payload_dict,
    single_response,
)
from src.core.errors import NotFoundError
from src.core.pagination import PaginationParams
from src.core.responses import ListResponse, SingleResponse
from src.domain.uow import UnitOfWork, UnitOfWorkFactory

_FIELDS = (
    "id",
    "role_id",
    "entity_type",
    "branch_id",
    "lab_id",
    "status_code",
    "role_name",
    "branch_name",
    "lab_name",
    "created_at",
    "updated_at",
)


async def _attach_names(uow: UnitOfWork, rows: list[Any]) -> None:
    """Attaches transient (non-persisted) *_name fields resolved from the
    role/branch/lab ids, so the generic CRUD table can show readable names
    without the caller needing a separate reference lookup."""
    role_names: dict[UUID, str] = {}
    branch_names: dict[UUID, str] = {}
    lab_names: dict[UUID, str] = {}

    async def _name(cache: dict[UUID, str], repo: Any, item_id: UUID | None) -> str | None:
        if item_id is None:
            return None
        if item_id not in cache:
            try:
                cache[item_id] = (await repo.read(item_id)).name
            except NotFoundError:
                return None
        return cache[item_id]

    for row in rows:
        row.role_name = await _name(role_names, uow.roles, row.role_id)
        row.branch_name = await _name(branch_names, uow.branches, row.branch_id)
        row.lab_name = await _name(lab_names, uow.labs, row.lab_id)


class RoleSubscriptionRuleCrudUseCase:
    def __init__(self, *, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def list(self, params: PaginationParams) -> ListResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            page = await uow.role_subscription_rules.list(params)
            await _attach_names(uow, page.items)
            return list_response(page, params, _FIELDS)

    async def read(self, item_id: UUID) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            row = await uow.role_subscription_rules.read(item_id)
            await _attach_names(uow, [row])
            return single_response(row, _FIELDS)

    async def create(self, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            row = await uow.role_subscription_rules.create(payload_dict(payload))
            await uow.commit()
            await _attach_names(uow, [row])
            return single_response(row, _FIELDS, operation="role_subscription_rules.create")

    async def update(self, item_id: UUID, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            row = await uow.role_subscription_rules.update(item_id, payload_dict(payload))
            await uow.commit()
            await _attach_names(uow, [row])
            return single_response(row, _FIELDS, operation="role_subscription_rules.update")

    async def delete(self, item_id: UUID) -> None:
        async with self._uow_factory() as uow:
            await uow.role_subscription_rules.delete(item_id)
            await uow.commit()
