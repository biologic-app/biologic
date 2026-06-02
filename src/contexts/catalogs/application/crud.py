from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel

from src.contexts.catalogs.infrastructure.repositories import (
    BranchRepository,
    ConclusionRepository,
    DirectionStatusRepository,
    DoctorRepository,
    IndicatorRepository,
    LabRepository,
    ObjectRepository,
    ProtocolTypeRepository,
    RepositoryPage,
    ResearchGoalRepository,
    ResearchStatusRepository,
    SampleStatusRepository,
    SampleTypeRepository,
    TestStatusRepository,
    reject_status_write,
)
from src.core.cursor_pagination import json_value
from src.core.pagination import PageMeta, PaginationParams
from src.core.responses import ListResponse, ResponseMeta, SingleResponse


class CatalogCrudUseCase:
    def __init__(
        self,
        *,
        branches: BranchRepository,
        labs: LabRepository,
        objects: ObjectRepository,
        doctors: DoctorRepository,
        sample_types: SampleTypeRepository,
        research_goals: ResearchGoalRepository,
        indicators: IndicatorRepository,
        conclusions: ConclusionRepository,
        protocol_types: ProtocolTypeRepository,
        direction_statuses: DirectionStatusRepository,
        sample_statuses: SampleStatusRepository,
        research_statuses: ResearchStatusRepository,
        test_statuses: TestStatusRepository,
    ) -> None:
        self.branches = branches
        self.labs = labs
        self.objects = objects
        self.doctors = doctors
        self.sample_types = sample_types
        self.research_goals = research_goals
        self.indicators = indicators
        self.conclusions = conclusions
        self.protocol_types = protocol_types
        self.direction_statuses = direction_statuses
        self.sample_statuses = sample_statuses
        self.research_statuses = research_statuses
        self.test_statuses = test_statuses

    async def list_branches(self, params: PaginationParams) -> ListResponse[dict[str, object]]:
        return _list_response(
            await self.branches.list(params),
            params,
            _branch_fields(),
        )

    async def read_branch(self, item_id: UUID) -> SingleResponse[dict[str, object]]:
        return _single_response(await self.branches.read(item_id), _branch_fields())

    async def create_branch(self, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        row = await self.branches.create(_payload(payload))
        return _single_response(row, _branch_fields(), operation="branches.create")

    async def update_branch(
        self,
        item_id: UUID,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        row = await self.branches.update(item_id, _payload(payload))
        return _single_response(row, _branch_fields(), operation="branches.update")

    async def delete_branch(self, item_id: UUID) -> None:
        await self.branches.delete(item_id)

    async def list_labs(self, params: PaginationParams) -> ListResponse[dict[str, object]]:
        return _list_response(await self.labs.list(params), params, _lab_fields(), ("branch",))

    async def read_lab(self, item_id: UUID) -> SingleResponse[dict[str, object]]:
        return _single_response(await self.labs.read(item_id), _lab_fields())

    async def create_lab(self, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        row = await self.labs.create(_payload(payload))
        return _single_response(row, _lab_fields(), operation="labs.create")

    async def update_lab(
        self,
        item_id: UUID,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        row = await self.labs.update(item_id, _payload(payload))
        return _single_response(row, _lab_fields(), operation="labs.update")

    async def delete_lab(self, item_id: UUID) -> None:
        await self.labs.delete(item_id)

    async def list_objects(self, params: PaginationParams) -> ListResponse[dict[str, object]]:
        return _list_response(
            await self.objects.list(params),
            params,
            _object_fields(),
            ("branch",),
        )

    async def read_object(self, item_id: UUID) -> SingleResponse[dict[str, object]]:
        return _single_response(await self.objects.read(item_id), _object_fields())

    async def create_object(self, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        row = await self.objects.create(_payload(payload))
        return _single_response(row, _object_fields(), operation="objects.create")

    async def update_object(
        self,
        item_id: UUID,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        row = await self.objects.update(item_id, _payload(payload))
        return _single_response(row, _object_fields(), operation="objects.update")

    async def delete_object(self, item_id: UUID) -> None:
        await self.objects.delete(item_id)

    async def list_doctors(self, params: PaginationParams) -> ListResponse[dict[str, object]]:
        return _list_response(await self.doctors.list(params), params, _doctor_fields())

    async def read_doctor(self, item_id: UUID) -> SingleResponse[dict[str, object]]:
        return _single_response(await self.doctors.read(item_id), _doctor_fields())

    async def create_doctor(self, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        row = await self.doctors.create(_payload(payload))
        return _single_response(row, _doctor_fields(), operation="doctors.create")

    async def update_doctor(
        self,
        item_id: UUID,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        row = await self.doctors.update(item_id, _payload(payload))
        return _single_response(row, _doctor_fields(), operation="doctors.update")

    async def delete_doctor(self, item_id: UUID) -> None:
        await self.doctors.delete(item_id)

    async def list_sample_types(self, params: PaginationParams) -> ListResponse[dict[str, object]]:
        return _list_response(await self.sample_types.list(params), params, _sample_type_fields())

    async def read_sample_type(self, item_id: UUID) -> SingleResponse[dict[str, object]]:
        return _single_response(await self.sample_types.read(item_id), _sample_type_fields())

    async def create_sample_type(self, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        row = await self.sample_types.create(_payload(payload))
        return _single_response(row, _sample_type_fields(), operation="sample_types.create")

    async def update_sample_type(
        self,
        item_id: UUID,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        row = await self.sample_types.update(item_id, _payload(payload))
        return _single_response(row, _sample_type_fields(), operation="sample_types.update")

    async def delete_sample_type(self, item_id: UUID) -> None:
        await self.sample_types.delete(item_id)

    async def list_research_goals(
        self,
        params: PaginationParams,
    ) -> ListResponse[dict[str, object]]:
        return _list_response(
            await self.research_goals.list(params),
            params,
            _research_goal_fields(),
            ("lab",),
        )

    async def read_research_goal(self, item_id: UUID) -> SingleResponse[dict[str, object]]:
        return _single_response(await self.research_goals.read(item_id), _research_goal_fields())

    async def create_research_goal(self, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        row = await self.research_goals.create(_payload(payload))
        return _single_response(row, _research_goal_fields(), operation="research_goals.create")

    async def update_research_goal(
        self,
        item_id: UUID,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        row = await self.research_goals.update(item_id, _payload(payload))
        return _single_response(row, _research_goal_fields(), operation="research_goals.update")

    async def delete_research_goal(self, item_id: UUID) -> None:
        await self.research_goals.delete(item_id)

    async def list_indicators(self, params: PaginationParams) -> ListResponse[dict[str, object]]:
        return _list_response(
            await self.indicators.list(params),
            params,
            _indicator_fields(),
            ("research_goal", "sample_type"),
        )

    async def read_indicator(self, item_id: UUID) -> SingleResponse[dict[str, object]]:
        return _single_response(await self.indicators.read(item_id), _indicator_fields())

    async def create_indicator(self, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        row = await self.indicators.create(_payload(payload))
        return _single_response(row, _indicator_fields(), operation="indicators.create")

    async def update_indicator(
        self,
        item_id: UUID,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        row = await self.indicators.update(item_id, _payload(payload))
        return _single_response(row, _indicator_fields(), operation="indicators.update")

    async def delete_indicator(self, item_id: UUID) -> None:
        await self.indicators.delete(item_id)

    async def list_conclusions(self, params: PaginationParams) -> ListResponse[dict[str, object]]:
        return _list_response(await self.conclusions.list(params), params, _conclusion_fields())

    async def read_conclusion(self, item_id: UUID) -> SingleResponse[dict[str, object]]:
        return _single_response(await self.conclusions.read(item_id), _conclusion_fields())

    async def create_conclusion(self, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        row = await self.conclusions.create(_payload(payload))
        return _single_response(row, _conclusion_fields(), operation="conclusions.create")

    async def update_conclusion(
        self,
        item_id: UUID,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        row = await self.conclusions.update(item_id, _payload(payload))
        return _single_response(row, _conclusion_fields(), operation="conclusions.update")

    async def delete_conclusion(self, item_id: UUID) -> None:
        await self.conclusions.delete(item_id)

    async def list_protocol_types(
        self,
        params: PaginationParams,
    ) -> ListResponse[dict[str, object]]:
        return _list_response(
            await self.protocol_types.list(params),
            params,
            _protocol_type_fields(),
        )

    async def read_protocol_type(self, item_id: UUID) -> SingleResponse[dict[str, object]]:
        return _single_response(await self.protocol_types.read(item_id), _protocol_type_fields())

    async def create_protocol_type(self, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        row = await self.protocol_types.create(_payload(payload))
        return _single_response(row, _protocol_type_fields(), operation="protocol_types.create")

    async def update_protocol_type(
        self,
        item_id: UUID,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        row = await self.protocol_types.update(item_id, _payload(payload))
        return _single_response(row, _protocol_type_fields(), operation="protocol_types.update")

    async def delete_protocol_type(self, item_id: UUID) -> None:
        await self.protocol_types.delete(item_id)

    async def list_direction_statuses(
        self,
        params: PaginationParams,
    ) -> ListResponse[dict[str, object]]:
        return _list_response(
            await self.direction_statuses.list(params),
            params,
            _status_fields(),
        )

    async def read_direction_status(self, item_id: UUID) -> SingleResponse[dict[str, object]]:
        return _single_response(await self.direction_statuses.read(item_id), _status_fields())

    async def update_direction_status(
        self,
        item_id: UUID,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        row = await self.direction_statuses.update(item_id, _payload(payload))
        return _single_response(row, _status_fields(), operation="direction_statuses.update")

    async def list_sample_statuses(
        self,
        params: PaginationParams,
    ) -> ListResponse[dict[str, object]]:
        return _list_response(await self.sample_statuses.list(params), params, _status_fields())

    async def read_sample_status(self, item_id: UUID) -> SingleResponse[dict[str, object]]:
        return _single_response(await self.sample_statuses.read(item_id), _status_fields())

    async def update_sample_status(
        self,
        item_id: UUID,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        row = await self.sample_statuses.update(item_id, _payload(payload))
        return _single_response(row, _status_fields(), operation="sample_statuses.update")

    async def list_research_statuses(
        self,
        params: PaginationParams,
    ) -> ListResponse[dict[str, object]]:
        return _list_response(await self.research_statuses.list(params), params, _status_fields())

    async def read_research_status(self, item_id: UUID) -> SingleResponse[dict[str, object]]:
        return _single_response(await self.research_statuses.read(item_id), _status_fields())

    async def update_research_status(
        self,
        item_id: UUID,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        row = await self.research_statuses.update(item_id, _payload(payload))
        return _single_response(row, _status_fields(), operation="research_statuses.update")

    async def list_test_statuses(self, params: PaginationParams) -> ListResponse[dict[str, object]]:
        return _list_response(await self.test_statuses.list(params), params, _status_fields())

    async def read_test_status(self, item_id: UUID) -> SingleResponse[dict[str, object]]:
        return _single_response(await self.test_statuses.read(item_id), _status_fields())

    async def update_test_status(
        self,
        item_id: UUID,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        row = await self.test_statuses.update(item_id, _payload(payload))
        return _single_response(row, _status_fields(), operation="test_statuses.update")

    def reject_read_only_status_write(self, resource: str) -> None:
        reject_status_write(resource)


def _payload(payload: BaseModel) -> dict[str, Any]:
    return payload.model_dump(mode="python", exclude_unset=True)


def _list_response(
    page: RepositoryPage,
    params: PaginationParams,
    fields: tuple[str, ...],
    allowed_includes: tuple[str, ...] = (),
) -> ListResponse[dict[str, object]]:
    requested = params.includes_requested
    applied = [item for item in requested if item in allowed_includes]
    return ListResponse(
        items=[_serialize(item, fields) for item in page.items],
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
    return SingleResponse(data=_serialize(item, fields), meta=ResponseMeta(operation=operation))


def _serialize(item: Any, fields: tuple[str, ...]) -> dict[str, object]:
    return {field: json_value(getattr(item, field)) for field in fields}


def _branch_fields() -> tuple[str, ...]:
    return ("id", "code", "name", "created_at", "updated_at")


def _lab_fields() -> tuple[str, ...]:
    return ("id", "branch_id", "code", "name", "full_name", "created_at", "updated_at")


def _object_fields() -> tuple[str, ...]:
    return (
        "id",
        "branch_id",
        "code",
        "name",
        "full_name",
        "address",
        "created_at",
        "updated_at",
    )


def _doctor_fields() -> tuple[str, ...]:
    return ("id", "first_name", "last_name", "patronymic", "created_at", "updated_at")


def _sample_type_fields() -> tuple[str, ...]:
    return ("id", "code", "name", "created_at", "updated_at")


def _research_goal_fields() -> tuple[str, ...]:
    return ("id", "code", "name", "comment", "lab_id", "created_at", "updated_at")


def _indicator_fields() -> tuple[str, ...]:
    return (
        "id",
        "name",
        "unit",
        "norm_text",
        "norm_value",
        "default_text",
        "comment",
        "research_goal_id",
        "sample_type_id",
        "created_at",
        "updated_at",
    )


def _conclusion_fields() -> tuple[str, ...]:
    return (
        "id",
        "code",
        "name",
        "text_singular",
        "text_plural",
        "comment",
        "created_at",
        "updated_at",
    )


def _protocol_type_fields() -> tuple[str, ...]:
    return ("id", "code", "name", "created_at", "updated_at")


def _status_fields() -> tuple[str, ...]:
    return ("id", "code", "name", "created_at", "updated_at")
