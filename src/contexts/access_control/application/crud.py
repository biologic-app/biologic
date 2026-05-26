from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel

from src.contexts.access_control.infrastructure.repositories import (
    PermissionRepository,
    RepositoryPage,
    RolePermissionRepository,
    RoleRepository,
    UserRepository,
    UserScopeRepository,
)
from src.core.cursor_pagination import json_value
from src.core.pagination import PageMeta, PaginationParams
from src.core.responses import ListResponse, ResponseMeta, SingleResponse


class AccessControlCrudUseCase:
    def __init__(
        self,
        *,
        users: UserRepository,
        roles: RoleRepository,
        permissions: PermissionRepository,
        role_permissions: RolePermissionRepository,
        user_scopes: UserScopeRepository,
    ) -> None:
        self.users = users
        self.roles = roles
        self.permissions = permissions
        self.role_permissions = role_permissions
        self.user_scopes = user_scopes

    async def list_users(self, params: PaginationParams) -> ListResponse[dict[str, object]]:
        return _list_response(await self.users.list(params), params, _user_fields())

    async def read_user(self, user_id: UUID) -> SingleResponse[dict[str, object]]:
        return _single_response(await self.users.read(user_id), _user_fields())

    async def create_user(self, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        row = await self.users.create(_payload(payload))
        return _single_response(row, _user_fields(), operation="users.create")

    async def update_user(
        self,
        user_id: UUID,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        row = await self.users.update(user_id, _payload(payload))
        return _single_response(row, _user_fields(), operation="users.update")

    async def delete_user(self, user_id: UUID) -> None:
        await self.users.delete(user_id)

    async def list_roles(self, params: PaginationParams) -> ListResponse[dict[str, object]]:
        return _list_response(await self.roles.list(params), params, _role_fields())

    async def read_role(self, role_id: UUID) -> SingleResponse[dict[str, object]]:
        return _single_response(await self.roles.read(role_id), _role_fields())

    async def create_role(self, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        row = await self.roles.create(_payload(payload))
        return _single_response(row, _role_fields(), operation="roles.create")

    async def update_role(
        self,
        role_id: UUID,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        row = await self.roles.update(role_id, _payload(payload))
        return _single_response(row, _role_fields(), operation="roles.update")

    async def delete_role(self, role_id: UUID) -> None:
        await self.roles.delete(role_id)

    async def list_permissions(self, params: PaginationParams) -> ListResponse[dict[str, object]]:
        return _list_response(
            await self.permissions.list(params),
            params,
            _permission_fields(),
        )

    async def read_permission(self, permission_id: UUID) -> SingleResponse[dict[str, object]]:
        return _single_response(await self.permissions.read(permission_id), _permission_fields())

    async def create_permission(self, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        row = await self.permissions.create(_payload(payload))
        return _single_response(row, _permission_fields(), operation="permissions.create")

    async def update_permission(
        self,
        permission_id: UUID,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        row = await self.permissions.update(permission_id, _payload(payload))
        return _single_response(row, _permission_fields(), operation="permissions.update")

    async def delete_permission(self, permission_id: UUID) -> None:
        await self.permissions.delete(permission_id)

    async def list_role_permissions(
        self,
        params: PaginationParams,
    ) -> ListResponse[dict[str, object]]:
        return _list_response(
            await self.role_permissions.list(params),
            params,
            _role_permission_fields(),
        )

    async def read_role_permission(
        self,
        role_permission_id: UUID,
    ) -> SingleResponse[dict[str, object]]:
        row = await self.role_permissions.read(role_permission_id)
        return _single_response(row, _role_permission_fields())

    async def create_role_permission(
        self,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        row = await self.role_permissions.create(_payload(payload))
        return _single_response(row, _role_permission_fields(), operation="role_permissions.create")

    async def update_role_permission(
        self,
        role_permission_id: UUID,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        row = await self.role_permissions.update(role_permission_id, _payload(payload))
        return _single_response(row, _role_permission_fields(), operation="role_permissions.update")

    async def delete_role_permission(self, role_permission_id: UUID) -> None:
        await self.role_permissions.delete(role_permission_id)

    async def list_user_scopes(self, params: PaginationParams) -> ListResponse[dict[str, object]]:
        return _list_response(await self.user_scopes.list(params), params, _user_scope_fields())

    async def read_user_scope(self, user_scope_id: UUID) -> SingleResponse[dict[str, object]]:
        return _single_response(await self.user_scopes.read(user_scope_id), _user_scope_fields())

    async def create_user_scope(self, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        row = await self.user_scopes.create(_payload(payload))
        return _single_response(row, _user_scope_fields(), operation="user_scopes.create")

    async def update_user_scope(
        self,
        user_scope_id: UUID,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        row = await self.user_scopes.update(user_scope_id, _payload(payload))
        return _single_response(row, _user_scope_fields(), operation="user_scopes.update")

    async def delete_user_scope(self, user_scope_id: UUID) -> None:
        await self.user_scopes.delete(user_scope_id)


def _payload(payload: BaseModel) -> dict[str, Any]:
    return payload.model_dump(mode="python", exclude_unset=True)


def _list_response(
    page: RepositoryPage,
    params: PaginationParams,
    fields: tuple[str, ...],
) -> ListResponse[dict[str, object]]:
    return ListResponse(
        items=[_serialize(item, fields) for item in page.items],
        meta=PageMeta(
            total=page.total,
            limit=params.limit,
            next_cursor=page.next_cursor,
            has_more=page.has_more,
            includes_requested=params.includes_requested,
            includes_applied=[],
            includes_allowed=[],
        ),
    )


def _single_response(
    item: Any,
    fields: tuple[str, ...],
    *,
    operation: str | None = None,
) -> SingleResponse[dict[str, object]]:
    return SingleResponse(data=_serialize(item, fields), meta=ResponseMeta(operation=operation))


def _serialize(item: Any, fields: tuple[str, ...]) -> dict[str, object]:
    return {field: json_value(getattr(item, field)) for field in fields}


def _user_fields() -> tuple[str, ...]:
    return (
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


def _role_fields() -> tuple[str, ...]:
    return ("id", "key", "name", "scope_type", "created_at", "updated_at")


def _permission_fields() -> tuple[str, ...]:
    return ("id", "resource", "action")


def _role_permission_fields() -> tuple[str, ...]:
    return ("id", "role_id", "permission_id")


def _user_scope_fields() -> tuple[str, ...]:
    return ("id", "user_id", "scope_id")
