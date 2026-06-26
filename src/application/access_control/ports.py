"""Repository ports for the access_control module."""

from __future__ import annotations

import builtins
from typing import Any, Protocol
from uuid import UUID

from src.core.pagination import PaginationParams
from src.infrastructure.repositories.access_control import RepositoryPage


class AccessControlCrudRepository(Protocol):
    async def list(self, params: PaginationParams) -> RepositoryPage: ...

    async def read(self, item_id: UUID) -> Any: ...

    async def create(self, values: dict[str, Any]) -> Any: ...

    async def update(self, item_id: UUID, values: dict[str, Any]) -> Any: ...

    async def delete(self, item_id: UUID) -> None: ...


class RolePermissionRepositoryPort(Protocol):
    async def list(self, params: PaginationParams) -> RepositoryPage: ...

    async def read(self, item_id: UUID) -> Any: ...

    async def create(self, values: dict[str, Any]) -> Any: ...

    async def update(self, item_id: UUID, values: dict[str, Any]) -> Any: ...

    async def delete(self, item_id: UUID) -> None: ...

    async def list_for_role(self, role_id: UUID) -> builtins.list[tuple[Any, Any]]: ...

    async def replace_for_role(
        self,
        role_id: UUID,
        permissions: builtins.list[dict[str, Any]],
    ) -> builtins.list[tuple[Any, Any]]: ...


class UserPermissionOverrideRepositoryPort(Protocol):
    async def list_for_user(self, user_id: UUID) -> builtins.list[tuple[Any, Any]]: ...

    async def replace_for_user(
        self,
        user_id: UUID,
        overrides: builtins.list[dict[str, Any]],
    ) -> builtins.list[tuple[Any, Any]]: ...
