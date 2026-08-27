from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import update

from src.application.access_control.use_cases._shared import (
    list_response,
    payload_dict,
    single_response,
)
from src.core.pagination import PaginationParams
from src.core.responses import ListResponse, SingleResponse
from src.domain.uow import UnitOfWorkFactory
from src.infrastructure.db.models import User

_FIELDS = ("id", "user_id", "scope_kind", "scope_id")


class UserScopeCrudUseCase:
    def __init__(self, *, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def list(self, params: PaginationParams) -> ListResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            return list_response(await uow.user_scopes.list(params), params, _FIELDS)

    async def read(self, item_id: UUID) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            return single_response(await uow.user_scopes.read(item_id), _FIELDS)

    async def create(self, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            row = await uow.user_scopes.create(payload_dict(payload))
            if getattr(uow, "session", None) is not None:
                await uow.session.execute(
                    update(User)
                    .where(User.id == row.user_id)
                    .values(token_version=User.token_version + 1)
                )
            await uow.commit()
            return single_response(row, _FIELDS, operation="user_scopes.create")

    async def update(self, item_id: UUID, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            current = await uow.user_scopes.read(item_id)
            row = await uow.user_scopes.update(item_id, payload_dict(payload))
            if getattr(uow, "session", None) is not None:
                await uow.session.execute(
                    update(User)
                    .where(User.id == current.user_id)
                    .values(token_version=User.token_version + 1)
                )
            await uow.commit()
            return single_response(row, _FIELDS, operation="user_scopes.update")

    async def delete(self, item_id: UUID) -> None:
        async with self._uow_factory() as uow:
            current = await uow.user_scopes.read(item_id)
            await uow.user_scopes.delete(item_id)
            if getattr(uow, "session", None) is not None:
                await uow.session.execute(
                    update(User)
                    .where(User.id == current.user_id)
                    .values(token_version=User.token_version + 1)
                )
            await uow.commit()
