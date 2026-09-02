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

_FIELDS = (
    "id",
    "username",
    "token_version",
    "status",
    "code",
    "first_name",
    "last_name",
    "patronymic",
    "role_id",
    "lab_id",
    "branch_id",
    "branch_name",
    "created_at",
    "updated_at",
)


class UserCrudUseCase:
    def __init__(self, *, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def list(self, params: PaginationParams) -> ListResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            return list_response(await uow.users.list(params), params, _FIELDS)

    async def read(self, item_id: UUID) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            return single_response(await uow.users.read(item_id), _FIELDS)

    async def create(self, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            role_id = payload.model_dump(exclude_unset=True).get("role_id")
            if role_id is not None:
                role = await uow.roles.read(role_id)
                if getattr(role, "is_system", False) or getattr(role, "key", None) == "superadmin":
                    raise ForbiddenError("The superadmin role cannot be assigned through the API.")
            row = await uow.users.create(payload_dict(payload))
            await uow.commit()
            return single_response(row, _FIELDS, operation="users.create")

    async def update(self, item_id: UUID, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            values = payload_dict(payload)
            # Version changes invalidate every access/refresh token for the
            # affected account.  The version itself is server-owned.
            values.pop("token_version", None)
            if "role_id" in values:
                role = await uow.roles.read(values["role_id"])
                if getattr(role, "is_system", False) or getattr(role, "key", None) == "superadmin":
                    raise ForbiddenError("The superadmin role cannot be assigned through the API.")
            row = await uow.users.update(item_id, values)
            if any(key in values for key in ("password_hash", "role_id", "status", "branch_id")):
                row.token_version = int(getattr(row, "token_version", 0)) + 1
                if hasattr(row, "refresh_token_version"):
                    row.refresh_token_version = row.token_version
            await uow.commit()
            return single_response(row, _FIELDS, operation="users.update")

    async def delete(self, item_id: UUID) -> None:
        async with self._uow_factory() as uow:
            await uow.users.delete(item_id)
            await uow.commit()
