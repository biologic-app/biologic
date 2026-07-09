"""Repository ports for the catalogs module.

These Protocols describe the reference-data repositories the single Unit of Work
exposes. The use cases depend on these ports; the concrete SQLAlchemy
implementations live in ``src.infrastructure.repositories.catalogs``.
"""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from src.core.pagination import PaginationParams
from src.infrastructure.repositories.catalogs import RepositoryPage


class CatalogCrudRepository(Protocol):
    """Full reference-data CRUD repository."""

    async def list(self, params: PaginationParams) -> RepositoryPage: ...

    async def read(self, item_id: UUID) -> Any: ...

    async def create(self, values: dict[str, Any]) -> Any: ...

    async def update(self, item_id: UUID, values: dict[str, Any]) -> Any: ...

    async def delete(self, item_id: UUID) -> None: ...


class CatalogStatusRepository(Protocol):
    """Read-only status reference repository that only allows name updates."""

    async def list(self, params: PaginationParams) -> RepositoryPage: ...

    async def read(self, item_id: UUID) -> Any: ...

    async def update(self, item_id: UUID, values: dict[str, Any]) -> Any: ...
