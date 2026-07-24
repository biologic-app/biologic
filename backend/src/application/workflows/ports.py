"""Repository port for the workflows module.

The Protocol describes the workflows repository exposed by the single Unit of
Work. Use cases depend on this port; the SQLAlchemy implementation lives in
``src.infrastructure.repositories.workflows``.
"""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from src.core.pagination import PaginationParams
from src.infrastructure.repositories.catalogs import RepositoryPage


class WorkflowsRepository(Protocol):
    # Templates -----------------------------------------------------------
    async def list_templates(self, params: PaginationParams) -> RepositoryPage: ...

    async def get_template(self, template_id: UUID) -> Any: ...

    async def create_template(self, values: dict[str, Any]) -> Any: ...

    async def update_template(self, template_id: UUID, values: dict[str, Any]) -> Any: ...

    async def delete_template(self, template_id: UUID) -> None: ...

    # Schema versions (immutable) ----------------------------------------
    async def list_versions(self, template_id: UUID) -> list[Any]: ...

    async def get_version(self, template_id: UUID, version: int) -> Any: ...

    async def next_version_number(self, template_id: UUID) -> int: ...

    async def create_version(
        self,
        template_id: UUID,
        version: int,
        schema: dict[str, Any],
    ) -> Any: ...

    # Runs ----------------------------------------------------------------
    async def list_runs(self, params: PaginationParams) -> RepositoryPage: ...

    async def get_run(self, run_id: UUID) -> Any: ...

    async def create_run(self, values: dict[str, Any]) -> Any: ...

    async def update_run(self, run_id: UUID, values: dict[str, Any]) -> Any: ...

    async def delete_run(self, run_id: UUID) -> None: ...

    async def set_run_status(self, run_id: UUID, status: str) -> Any: ...

    # Events (append-only) -----------------------------------------------
    async def append_event(
        self,
        run_id: UUID,
        kind: str,
        node_id: str | None,
        payload: dict[str, Any],
        author: str | None,
    ) -> Any: ...

    async def list_events(self, run_id: UUID) -> list[Any]: ...

    # Step executions (idempotency guard) --------------------------------
    async def find_step_execution(
        self,
        run_id: UUID,
        node_id: str,
        attempt: int,
    ) -> Any: ...

    async def record_step_execution(
        self,
        run_id: UUID,
        node_id: str,
        attempt: int,
        status: str,
        result: dict[str, Any],
    ) -> Any: ...

    # Attachments ---------------------------------------------------------
    async def create_attachment(
        self,
        run_id: UUID,
        field_id: str,
        filename: str,
        content_type: str | None,
        size_bytes: int,
        data: bytes,
    ) -> Any: ...

    async def get_attachment(self, attachment_id: UUID) -> Any: ...

    # Domain correlation read (execute-step pre-check) -------------------
    async def read_status_code(self, resource: str, entity_id: UUID) -> str | None: ...
