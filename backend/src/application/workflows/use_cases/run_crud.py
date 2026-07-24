from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from src.application.workflows.use_cases._shared import (
    EVENT_FIELDS,
    RUN_FIELDS,
    list_response,
    payload_dict,
    serialize,
    single_response,
)
from src.core.pagination import PaginationParams
from src.core.responses import ListResponse, SingleResponse
from src.domain.uow import UnitOfWorkFactory

_INCLUDE_EVENTS = "events"


class WorkflowRunUseCase:
    def __init__(self, *, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def list(self, params: PaginationParams) -> ListResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            return list_response(await uow.workflows.list_runs(params), params, RUN_FIELDS)

    async def read(
        self,
        run_id: UUID,
        *,
        includes: Sequence[str] | None = None,
    ) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            run = await uow.workflows.get_run(run_id)
            data: dict[str, Any] = serialize(run, RUN_FIELDS)
            if includes and _INCLUDE_EVENTS in includes:
                events = await uow.workflows.list_events(run_id)
                data[_INCLUDE_EVENTS] = [serialize(e, EVENT_FIELDS) for e in events]
            return single_response(data)

    async def create(self, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            values = payload_dict(payload)
            template = await uow.workflows.get_template(values["template_id"])
            values.setdefault("schema_version", template.current_version)
            run = await uow.workflows.create_run(values)
            await uow.commit()
            return single_response(
                serialize(run, RUN_FIELDS),
                operation="workflows.runs.create",
            )

    async def update(self, run_id: UUID, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            run = await uow.workflows.update_run(run_id, payload_dict(payload))
            await uow.commit()
            return single_response(
                serialize(run, RUN_FIELDS),
                operation="workflows.runs.update",
            )

    async def delete(self, run_id: UUID) -> None:
        async with self._uow_factory() as uow:
            await uow.workflows.delete_run(run_id)
            await uow.commit()

    async def complete(self, run_id: UUID) -> SingleResponse[dict[str, object]]:
        return await self._set_status(run_id, "completed", "workflows.runs.complete")

    async def archive(self, run_id: UUID) -> SingleResponse[dict[str, object]]:
        return await self._set_status(run_id, "archived", "workflows.runs.archive")

    async def add_comment(
        self,
        run_id: UUID,
        text: str,
        *,
        node_id: str | None = None,
        author: str | None = None,
    ) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            await uow.workflows.get_run(run_id)
            event = await uow.workflows.append_event(
                run_id=run_id,
                kind="comment",
                node_id=node_id,
                payload={"text": text},
                author=author,
            )
            await uow.commit()
            return single_response(
                serialize(event, EVENT_FIELDS),
                operation="workflows.runs.comment",
            )

    async def _set_status(
        self,
        run_id: UUID,
        status: str,
        operation: str,
    ) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            run = await uow.workflows.set_run_status(run_id, status)
            await uow.commit()
            return single_response(serialize(run, RUN_FIELDS), operation=operation)
