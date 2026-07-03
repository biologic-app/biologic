from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel

from src.contexts.laboratory_workflow.application.direction_sample_import import (
    DirectionExcelImportService,
    DirectionJsonImportService,
)
from src.contexts.laboratory_workflow.application.imports import DirectionImportService
from src.contexts.laboratory_workflow.application.legacy_direction_import import (
    LegacyDirectionXlsImportService,
)
from src.contexts.laboratory_workflow.infrastructure.crud_repositories import (
    DirectionCrudRepository,
    ProtocolCrudRepository,
    RepositoryPage,
    ResearchCrudRepository,
    SampleCrudRepository,
    TestCrudRepository,
    reject_test_create,
)
from src.core.cursor_pagination import json_value
from src.core.pagination import PageMeta, PaginationParams
from src.core.responses import ListResponse, ResponseMeta, SingleResponse


class WorkflowCrudUseCase:
    def __init__(
        self,
        *,
        directions: DirectionCrudRepository,
        samples: SampleCrudRepository,
        research: ResearchCrudRepository,
        tests: TestCrudRepository,
        protocols: ProtocolCrudRepository,
    ) -> None:
        self.directions = directions
        self.samples = samples
        self.research = research
        self.tests = tests
        self.protocols = protocols

    async def list_directions(
        self, params: PaginationParams
    ) -> ListResponse[dict[str, object]]:
        return _list_response(
            await self.directions.list(params),
            params,
            _direction_fields(),
            ("status", "doctor", "object"),
        )

    async def read_direction(
        self, direction_id: UUID
    ) -> SingleResponse[dict[str, object]]:
        return _single_response(
            await self.directions.read(direction_id), _direction_fields()
        )

    async def create_direction(
        self, payload: BaseModel, *, actor_id: UUID | None = None
    ) -> SingleResponse[dict[str, object]]:
        row = await self.directions.create(_payload(payload), created_by=actor_id)
        return _single_response(row, _direction_fields(), operation="directions.create")

    async def update_direction(
        self,
        direction_id: UUID,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        row = await self.directions.update(direction_id, _payload(payload))
        return _single_response(row, _direction_fields(), operation="directions.update")

    async def delete_direction(self, direction_id: UUID) -> None:
        await self.directions.delete(direction_id)

    async def import_directions(
        self, filename: str, content: bytes
    ) -> SingleResponse[dict[str, object]]:
        summary = await DirectionImportService(directions=self.directions).import_file(
            filename, content
        )
        return SingleResponse(
            data=summary.model_dump(mode="json"),
            meta=ResponseMeta(operation="directions.import"),
        )

    async def import_directions_excel(
        self, filename: str, content: bytes, *, actor_id: UUID | None = None
    ) -> SingleResponse[dict[str, object]]:
        summary = await DirectionExcelImportService(
            directions=self.directions, samples=self.samples, created_by=actor_id
        ).import_file(filename, content)
        return SingleResponse(
            data=summary.model_dump(mode="json"),
            meta=ResponseMeta(operation="directions.import_excel"),
        )

    async def import_directions_json(
        self, filename: str, content: bytes, *, actor_id: UUID | None = None
    ) -> SingleResponse[dict[str, object]]:
        summary = await DirectionJsonImportService(
            directions=self.directions, samples=self.samples, created_by=actor_id
        ).import_file(filename, content)
        return SingleResponse(
            data=summary.model_dump(mode="json"),
            meta=ResponseMeta(operation="directions.import_json"),
        )

    async def import_directions_legacy_xls(
        self, filename: str, content: bytes, *, actor_id: UUID | None = None
    ) -> SingleResponse[dict[str, object]]:
        summary = await LegacyDirectionXlsImportService(
            directions=self.directions,
            samples=self.samples,
            research=self.research,
            created_by=actor_id,
        ).import_file(filename, content)
        return SingleResponse(
            data=summary.model_dump(mode="json"),
            meta=ResponseMeta(operation="directions.import_legacy_xls"),
        )

    async def list_samples(
        self, params: PaginationParams
    ) -> ListResponse[dict[str, object]]:
        return _list_response(
            await self.samples.list(params),
            params,
            _sample_fields(),
            ("status", "direction", "sample_type", "protocol"),
        )

    async def read_sample(self, sample_id: UUID) -> SingleResponse[dict[str, object]]:
        return _single_response(await self.samples.read(sample_id), _sample_fields())

    async def create_sample(
        self, payload: BaseModel
    ) -> SingleResponse[dict[str, object]]:
        row = await self.samples.create(_payload(payload))
        return _single_response(row, _sample_fields(), operation="samples.create")

    async def update_sample(
        self,
        sample_id: UUID,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        row = await self.samples.update(sample_id, _payload(payload))
        return _single_response(row, _sample_fields(), operation="samples.update")

    async def delete_sample(self, sample_id: UUID) -> None:
        await self.samples.delete(sample_id)

    async def list_research(
        self, params: PaginationParams
    ) -> ListResponse[dict[str, object]]:
        return _list_response(
            await self.research.list(params),
            params,
            _research_fields(),
            ("status", "sample", "research_goal", "lab"),
        )

    async def read_research(
        self, research_id: UUID
    ) -> SingleResponse[dict[str, object]]:
        return _single_response(
            await self.research.read(research_id), _research_fields()
        )

    async def create_research(
        self, payload: BaseModel
    ) -> SingleResponse[dict[str, object]]:
        row = await self.research.create(_payload(payload))
        return _single_response(row, _research_fields(), operation="research.create")

    async def update_research(
        self,
        research_id: UUID,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        row = await self.research.update(research_id, _payload(payload))
        return _single_response(row, _research_fields(), operation="research.update")

    async def delete_research(self, research_id: UUID) -> None:
        await self.research.delete(research_id)

    async def list_tests(
        self, params: PaginationParams
    ) -> ListResponse[dict[str, object]]:
        return _list_response(
            await self.tests.list(params),
            params,
            _test_fields(),
            ("status", "research", "indicator"),
        )

    async def read_test(self, test_id: UUID) -> SingleResponse[dict[str, object]]:
        return _single_response(await self.tests.read(test_id), _test_fields())

    def reject_test_create(self) -> None:
        reject_test_create()

    async def update_test(
        self,
        test_id: UUID,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        row = await self.tests.update(test_id, _payload(payload))
        return _single_response(row, _test_fields(), operation="tests.update")

    async def delete_test(self, test_id: UUID) -> None:
        await self.tests.delete(test_id)

    async def list_protocols(
        self, params: PaginationParams
    ) -> ListResponse[dict[str, object]]:
        return _list_response(
            await self.protocols.list(params),
            params,
            _protocol_fields(),
            ("conclusion", "protocol_type"),
        )

    async def read_protocol(
        self, protocol_id: UUID
    ) -> SingleResponse[dict[str, object]]:
        return _single_response(
            await self.protocols.read(protocol_id), _protocol_fields()
        )

    async def delete_protocol(self, protocol_id: UUID) -> None:
        await self.protocols.delete(protocol_id)


def _payload(payload: BaseModel) -> dict[str, Any]:
    return payload.model_dump(mode="python", exclude_unset=True)


def _list_response(
    page: RepositoryPage,
    params: PaginationParams,
    fields: tuple[str, ...],
    allowed_includes: tuple[str, ...],
) -> ListResponse[dict[str, object]]:
    requested = params.includes_requested
    applied = [item for item in requested if item in allowed_includes]
    return ListResponse(
        items=[_serialize(item, fields, tuple(applied)) for item in page.items],
        meta=PageMeta(
            total=page.total,
            limit=params.limit,
            next_cursor=page.next_cursor,
            has_more=page.has_more,
            includes_requested=requested,
            includes_applied=applied,
            includes_allowed=list(allowed_includes),
        ),
    )


def _single_response(
    item: Any,
    fields: tuple[str, ...],
    *,
    operation: str | None = None,
) -> SingleResponse[dict[str, object]]:
    return SingleResponse(
        data=_serialize(item, fields), meta=ResponseMeta(operation=operation)
    )


def _serialize(
    item: Any,
    fields: tuple[str, ...],
    includes: tuple[str, ...] = (),
) -> dict[str, object]:
    payload = {field: _json_value(getattr(item, field)) for field in fields}
    for include in includes:
        if hasattr(item, include):
            payload[include] = _json_value(getattr(item, include))
    return payload


def _json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return json_value(value)


def _direction_fields() -> tuple[str, ...]:
    return (
        "id",
        "year_no",
        "base_no",
        "is_done",
        "is_urgent",
        "doctor_id",
        "object_id",
        "status_id",
        "created_by",
        "sampled_at",
        "received_at",
        "completed_at",
        "import_warnings",
        "created_at",
        "updated_at",
    )


def _sample_fields() -> tuple[str, ...]:
    return (
        "id",
        "month_no",
        "name",
        "alternate_name",
        "mass",
        "target_description",
        "comment",
        "section",
        "delivery",
        "nomenclature_code",
        "batch_code",
        "supplier",
        "is_urgent",
        "is_done",
        "sample_type_id",
        "status_id",
        "direction_id",
        "protocol_id",
        "sampled_at",
        "received_at",
        "completed_at",
        "deadline",
        "verdict",
        "created_at",
        "updated_at",
    )


def _research_fields() -> tuple[str, ...]:
    return (
        "id",
        "sample_id",
        "research_goal_id",
        "lab_id",
        "comment",
        "recommendation",
        "status_id",
        "received_at",
        "completed_at",
        "created_at",
        "updated_at",
    )


def _test_fields() -> tuple[str, ...]:
    return (
        "id",
        "value",
        "comment",
        "norm",
        "is_active",
        "research_id",
        "indicator_id",
        "status_id",
        "created_at",
        "updated_at",
    )


def _protocol_fields() -> tuple[str, ...]:
    return (
        "id",
        "year_no",
        "copies",
        "is_signed",
        "protocol_copy_name",
        "excerpt_copy_name",
        "conclusion_id",
        "protocol_type_id",
        "issued_at",
        "created_at",
        "updated_at",
    )
