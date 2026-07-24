from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from src.application.workflows.use_cases._shared import (
    TEMPLATE_FIELDS,
    VERSION_FIELDS,
    list_response,
    payload_dict,
    serialize,
    single_response,
)
from src.core.pagination import PaginationParams
from src.core.responses import ListResponse, SingleResponse
from src.domain.uow import UnitOfWorkFactory
from src.domain.workflows.schema import validate_workflow_schema

_INCLUDE_VERSIONS = "versions"


class WorkflowTemplateUseCase:
    def __init__(self, *, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def list(self, params: PaginationParams) -> ListResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            page = await uow.workflows.list_templates(params)
            return list_response(page, params, TEMPLATE_FIELDS)

    async def read(
        self,
        template_id: UUID,
        *,
        includes: Sequence[str] | None = None,
    ) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            template = await uow.workflows.get_template(template_id)
            data: dict[str, Any] = serialize(template, TEMPLATE_FIELDS)
            if includes and _INCLUDE_VERSIONS in includes:
                versions = await uow.workflows.list_versions(template_id)
                data[_INCLUDE_VERSIONS] = [serialize(v, VERSION_FIELDS) for v in versions]
            return single_response(data)

    async def create(self, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            template = await uow.workflows.create_template(payload_dict(payload))
            await uow.commit()
            return single_response(
                serialize(template, TEMPLATE_FIELDS),
                operation="workflows.templates.create",
            )

    async def update(
        self,
        template_id: UUID,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            template = await uow.workflows.update_template(template_id, payload_dict(payload))
            await uow.commit()
            return single_response(
                serialize(template, TEMPLATE_FIELDS),
                operation="workflows.templates.update",
            )

    async def delete(self, template_id: UUID) -> None:
        async with self._uow_factory() as uow:
            await uow.workflows.delete_template(template_id)
            await uow.commit()

    async def create_version(
        self,
        template_id: UUID,
        schema: dict[str, Any],
    ) -> SingleResponse[dict[str, object]]:
        # Validate the v2 format before persisting: versions are immutable, so a
        # malformed schema must be rejected up front (422).
        validate_workflow_schema(schema)
        async with self._uow_factory() as uow:
            await uow.workflows.get_template(template_id)
            version_number = await uow.workflows.next_version_number(template_id)
            version = await uow.workflows.create_version(template_id, version_number, schema)
            await uow.workflows.update_template(
                template_id,
                {"current_version": version_number},
            )
            await uow.commit()
            return single_response(
                serialize(version, VERSION_FIELDS),
                operation="workflows.templates.create_version",
            )
