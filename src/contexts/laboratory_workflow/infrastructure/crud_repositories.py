from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, asc, delete, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.crud_query import (
    JoinSpec,
    RelatedField,
    apply_outer_joins,
    attach_sort_values,
    build_crud_query_parts,
    cursor_sort_value,
)
from src.core.cursor_pagination import (
    CursorState,
    decode_cursor,
    encode_cursor,
    json_value,
)
from src.core.errors import BadRequestError, DomainConflictError, NotFoundError
from src.core.pagination import PaginationParams
from src.infrastructure.db.models import (
    ChangeLog,
    Conclusion,
    Direction,
    DirectionStatus,
    Doctor,
    Indicator,
    Lab,
    Object,
    Protocol,
    ProtocolType,
    Research,
    ResearchGoal,
    ResearchStatus,
    Sample,
    SampleStatus,
    SampleType,
    Test,
    TestStatus,
)


@dataclass(frozen=True)
class RepositoryPage:
    items: list[Any]
    total: int
    has_more: bool
    next_cursor: str | None


class DirectionCrudRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        page = await _list_rows(
            self.session, Direction, params, _direction_sortable_fields()
        )
        await _populate_direction_includes(
            self.session, page.items, params.includes_requested
        )
        return page

    async def read(self, direction_id: UUID) -> Any:
        return await _read_row(self.session, Direction, "directions", direction_id)

    async def create(self, values: dict[str, Any]) -> Any:
        return await _create_row(
            self.session, Direction, _pick(values, _direction_write_fields())
        )

    async def update(self, direction_id: UUID, values: dict[str, Any]) -> Any:
        _reject_status_update("directions", values)
        return await _update_row(
            self.session,
            await self.read(direction_id),
            _pick(values, _direction_write_fields()),
            audit_resource="directions",
        )

    async def delete(self, direction_id: UUID) -> None:
        await _delete_row(self.session, await self.read(direction_id))


class SampleCrudRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        page = await _list_rows(self.session, Sample, params, _sample_sortable_fields())
        await _populate_sample_includes(
            self.session, page.items, params.includes_requested
        )
        return page

    async def read(self, sample_id: UUID) -> Any:
        return await _read_row(self.session, Sample, "samples", sample_id)

    async def create(self, values: dict[str, Any]) -> Any:
        return await _create_row(
            self.session, Sample, _pick(values, _sample_write_fields())
        )

    async def update(self, sample_id: UUID, values: dict[str, Any]) -> Any:
        _reject_status_update("samples", values)
        return await _update_row(
            self.session,
            await self.read(sample_id),
            _pick(values, _sample_write_fields()),
            audit_resource="samples",
        )

    async def delete(self, sample_id: UUID) -> None:
        await _delete_row(self.session, await self.read(sample_id))


class ResearchCrudRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        page = await _list_rows(
            self.session, Research, params, _research_sortable_fields()
        )
        await _populate_research_includes(
            self.session, page.items, params.includes_requested
        )
        return page

    async def read(self, research_id: UUID) -> Any:
        return await _read_row(self.session, Research, "research", research_id)

    async def create(self, values: dict[str, Any]) -> Any:
        return await _create_row(
            self.session, Research, _pick(values, _research_write_fields())
        )

    async def update(self, research_id: UUID, values: dict[str, Any]) -> Any:
        _reject_status_update("research", values)
        return await _update_row(
            self.session,
            await self.read(research_id),
            _pick(values, _research_write_fields()),
            audit_resource="research",
        )

    async def delete(self, research_id: UUID) -> None:
        await _delete_row(self.session, await self.read(research_id))


class TestCrudRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        page = await _list_rows(self.session, Test, params, _test_sortable_fields())
        await _populate_test_includes(
            self.session, page.items, params.includes_requested
        )
        return page

    async def read(self, test_id: UUID) -> Any:
        return await _read_row(self.session, Test, "tests", test_id)

    async def update(self, test_id: UUID, values: dict[str, Any]) -> Any:
        _reject_status_update("tests", values)
        return await _update_row(
            self.session,
            await self.read(test_id),
            _pick(values, _test_write_fields()),
            audit_resource="tests",
        )

    async def delete(self, test_id: UUID) -> None:
        await _delete_row(self.session, await self.read(test_id))


class ProtocolCrudRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        return await _list_rows(
            self.session, Protocol, params, _protocol_sortable_fields()
        )

    async def read(self, protocol_id: UUID) -> Any:
        return await _read_row(self.session, Protocol, "protocols", protocol_id)

    async def delete(self, protocol_id: UUID) -> None:
        await _delete_row(self.session, await self.read(protocol_id))


def reject_test_create() -> None:
    raise DomainConflictError(
        code="resource_read_only",
        detail="tests cannot be created through generic CRUD.",
    )


async def _list_rows(
    session: AsyncSession,
    model: type[Any],
    params: PaginationParams,
    sortable_fields: tuple[str, ...],
) -> RepositoryPage:
    query_parts = build_crud_query_parts(
        model=model,
        params=params,
        sortable_fields=sortable_fields,
        base_filters=_base_filters(model),
        related_fields=_related_fields(model),
    )
    sort_by = query_parts.sort_by
    sort_column = query_parts.sort_column
    id_column = getattr(model, "id")
    filters = list(query_parts.filters)
    total_filters = list(filters)
    cursor = decode_cursor(params.cursor) if params.cursor else None
    if cursor is not None:
        if cursor.sort_by != sort_by or cursor.sort_order != params.sort_order:
            raise BadRequestError("Pagination cursor does not match requested sorting.")
        filters.append(_cursor_filter(cursor, sort_column, id_column))

    total_query = apply_outer_joins(
        select(func.count()).select_from(model),
        query_parts.joins,
    ).where(*total_filters)
    total_result = await session.execute(total_query)
    total = int(total_result.scalar_one())
    order_fn = asc if params.sort_order == "asc" else desc
    query = apply_outer_joins(
        select(model, sort_column),
        query_parts.joins,
    )
    query = (
        query.where(*filters)
        .order_by(order_fn(sort_column), order_fn(id_column))
        .limit(params.limit + 1)
    )
    result = await session.execute(query)
    rows = attach_sort_values(list(result.all()))
    items = rows[: params.limit]
    has_more = len(rows) > params.limit
    next_cursor = _next_cursor(items, sort_by, params.sort_order) if has_more else None
    return RepositoryPage(
        items=items, total=total, has_more=has_more, next_cursor=next_cursor
    )


async def _read_row(
    session: AsyncSession,
    model: type[Any],
    resource: str,
    item_id: UUID,
) -> Any:
    result = await session.execute(
        select(model).where(getattr(model, "id") == item_id, *_base_filters(model)),
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise NotFoundError(f"{resource} item {item_id} was not found.")
    return row


async def _create_row(
    session: AsyncSession, model: type[Any], values: dict[str, Any]
) -> Any:
    row = model(**values)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def _update_row(
    session: AsyncSession,
    row: Any,
    values: dict[str, Any],
    *,
    audit_resource: str,
) -> Any:
    diff = _audit_diff(row, values)
    for field, value in values.items():
        setattr(row, field, value)
    if hasattr(row, "updated_at"):
        setattr(row, "updated_at", datetime.now(UTC))
    session.add(row)
    if diff:
        session.add(
            ChangeLog(
                entity_type=audit_resource,
                entity_id=row.id,
                action=f"{audit_resource}.update",
                actor_name="api",
                snapshot={field: change["to"] for field, change in diff.items()},
                diff=diff,
            ),
        )
    await session.commit()
    await session.refresh(row)
    return row


def _audit_diff(row: Any, values: dict[str, Any]) -> dict[str, dict[str, Any]]:
    diff: dict[str, dict[str, Any]] = {}
    for field, next_value in values.items():
        previous_value = getattr(row, field)
        if previous_value == next_value:
            continue
        diff[field] = {
            "from": json_value(previous_value),
            "to": json_value(next_value),
        }
    return diff


async def _delete_row(session: AsyncSession, row: Any) -> None:
    if hasattr(row, "deleted_at"):
        setattr(row, "deleted_at", datetime.now(UTC))
        if hasattr(row, "updated_at"):
            setattr(row, "updated_at", datetime.now(UTC))
        session.add(row)
    else:
        await session.execute(delete(type(row)).where(type(row).id == row.id))
    await session.commit()


def _reject_status_update(resource: str, values: dict[str, Any]) -> None:
    if "status_id" in values:
        raise DomainConflictError(
            code="invalid_status_transition",
            detail=f"{resource} lifecycle status must be changed through commands.",
        )


def _base_filters(model: type[Any]) -> list[Any]:
    if hasattr(model, "deleted_at"):
        return [getattr(model, "deleted_at").is_(None)]
    return []


async def _populate_research_includes(
    session: AsyncSession,
    items: list[Any],
    includes_requested: list[str],
) -> None:
    includes = set(includes_requested) & {"sample", "research_goal", "lab", "status"}
    if not items or not includes:
        return

    if "sample" in includes:
        sample_ids = {item.sample_id for item in items if item.sample_id is not None}
        samples = await _research_sample_includes(session, sample_ids)
        for item in items:
            setattr(item, "sample", samples.get(item.sample_id))

    if "research_goal" in includes:
        research_goal_ids = {
            item.research_goal_id for item in items if item.research_goal_id is not None
        }
        research_goals = await _research_goal_includes(session, research_goal_ids)
        for item in items:
            setattr(item, "research_goal", research_goals.get(item.research_goal_id))

    if "lab" in includes:
        lab_ids = {item.lab_id for item in items if item.lab_id is not None}
        labs = await _lab_includes(session, lab_ids)
        for item in items:
            setattr(item, "lab", labs.get(item.lab_id))

    if "status" in includes:
        status_ids = {item.status_id for item in items if item.status_id is not None}
        statuses = await _research_status_includes(session, status_ids)
        for item in items:
            setattr(item, "status", statuses.get(item.status_id))


async def _populate_direction_includes(
    session: AsyncSession,
    items: list[Any],
    includes_requested: list[str],
) -> None:
    includes = set(includes_requested) & {"status"}
    if not items or not includes:
        return

    status_ids = {item.status_id for item in items if item.status_id is not None}
    statuses = await _direction_status_includes(session, status_ids)
    for item in items:
        setattr(item, "status", statuses.get(item.status_id))


async def _populate_sample_includes(
    session: AsyncSession,
    items: list[Any],
    includes_requested: list[str],
) -> None:
    includes = set(includes_requested) & {"status"}
    if not items or not includes:
        return

    status_ids = {item.status_id for item in items if item.status_id is not None}
    statuses = await _sample_status_includes(session, status_ids)
    for item in items:
        setattr(item, "status", statuses.get(item.status_id))


async def _populate_test_includes(
    session: AsyncSession,
    items: list[Any],
    includes_requested: list[str],
) -> None:
    includes = set(includes_requested) & {"research", "indicator", "status"}
    if not items or not includes:
        return

    if "research" in includes:
        research_ids = {item.research_id for item in items if item.research_id is not None}
        research = await _test_research_includes(session, research_ids)
        for item in items:
            setattr(item, "research", research.get(item.research_id))

    if "indicator" in includes:
        indicator_ids = {
            item.indicator_id for item in items if item.indicator_id is not None
        }
        indicators = await _indicator_includes(session, indicator_ids)
        for item in items:
            setattr(item, "indicator", indicators.get(item.indicator_id))

    if "status" in includes:
        status_ids = {item.status_id for item in items if item.status_id is not None}
        statuses = await _test_status_includes(session, status_ids)
        for item in items:
            setattr(item, "status", statuses.get(item.status_id))


async def _direction_status_includes(
    session: AsyncSession,
    status_ids: set[UUID],
) -> dict[UUID, dict[str, object]]:
    if not status_ids:
        return {}
    result = await session.execute(
        select(DirectionStatus.id, DirectionStatus.code, DirectionStatus.name).where(
            DirectionStatus.id.in_(status_ids),
            *_base_filters(DirectionStatus),
        ),
    )
    return {
        row_id: {"id": row_id, "code": code, "name": name}
        for row_id, code, name in result.all()
    }


async def _sample_status_includes(
    session: AsyncSession,
    status_ids: set[UUID],
) -> dict[UUID, dict[str, object]]:
    if not status_ids:
        return {}
    result = await session.execute(
        select(SampleStatus.id, SampleStatus.code, SampleStatus.name).where(
            SampleStatus.id.in_(status_ids),
            *_base_filters(SampleStatus),
        ),
    )
    return {
        row_id: {"id": row_id, "code": code, "name": name}
        for row_id, code, name in result.all()
    }


async def _test_research_includes(
    session: AsyncSession,
    research_ids: set[UUID],
) -> dict[UUID, dict[str, object]]:
    if not research_ids:
        return {}
    result = await session.execute(
        select(Research.id, Research.sample_id, Research.research_goal_id).where(
            Research.id.in_(research_ids),
            *_base_filters(Research),
        ),
    )
    return {
        row_id: {
            "id": row_id,
            "sample_id": sample_id,
            "research_goal_id": research_goal_id,
        }
        for row_id, sample_id, research_goal_id in result.all()
    }


async def _indicator_includes(
    session: AsyncSession,
    indicator_ids: set[UUID],
) -> dict[UUID, dict[str, object]]:
    if not indicator_ids:
        return {}
    result = await session.execute(
        select(Indicator.id, Indicator.name, Indicator.unit, Indicator.norm_text).where(
            Indicator.id.in_(indicator_ids),
            *_base_filters(Indicator),
        ),
    )
    return {
        row_id: {
            "id": row_id,
            "name": name,
            "unit": unit,
            "norm_text": norm_text,
        }
        for row_id, name, unit, norm_text in result.all()
    }


async def _test_status_includes(
    session: AsyncSession,
    status_ids: set[UUID],
) -> dict[UUID, dict[str, object]]:
    if not status_ids:
        return {}
    result = await session.execute(
        select(TestStatus.id, TestStatus.code, TestStatus.name).where(
            TestStatus.id.in_(status_ids),
            *_base_filters(TestStatus),
        ),
    )
    return {
        row_id: {"id": row_id, "code": code, "name": name}
        for row_id, code, name in result.all()
    }


async def _research_sample_includes(
    session: AsyncSession,
    sample_ids: set[UUID],
) -> dict[UUID, dict[str, object]]:
    if not sample_ids:
        return {}
    result = await session.execute(
        select(Sample.id, Sample.name).where(
            Sample.id.in_(sample_ids), *_base_filters(Sample)
        ),
    )
    return {row_id: {"id": row_id, "name": name} for row_id, name in result.all()}


async def _research_goal_includes(
    session: AsyncSession,
    research_goal_ids: set[UUID],
) -> dict[UUID, dict[str, object]]:
    if not research_goal_ids:
        return {}
    result = await session.execute(
        select(ResearchGoal.id, ResearchGoal.code, ResearchGoal.name).where(
            ResearchGoal.id.in_(research_goal_ids),
            *_base_filters(ResearchGoal),
        ),
    )
    return {
        row_id: {"id": row_id, "code": code, "name": name}
        for row_id, code, name in result.all()
    }


async def _lab_includes(
    session: AsyncSession,
    lab_ids: set[UUID],
) -> dict[UUID, dict[str, object]]:
    if not lab_ids:
        return {}
    result = await session.execute(
        select(Lab.id, Lab.code, Lab.name).where(
            Lab.id.in_(lab_ids), *_base_filters(Lab)
        ),
    )
    return {
        row_id: {"id": row_id, "code": code, "name": name}
        for row_id, code, name in result.all()
    }


async def _research_status_includes(
    session: AsyncSession,
    status_ids: set[UUID],
) -> dict[UUID, dict[str, object]]:
    if not status_ids:
        return {}
    result = await session.execute(
        select(ResearchStatus.id, ResearchStatus.code, ResearchStatus.name).where(
            ResearchStatus.id.in_(status_ids),
            *_base_filters(ResearchStatus),
        ),
    )
    return {
        row_id: {"id": row_id, "code": code, "name": name}
        for row_id, code, name in result.all()
    }


def _related_fields(model: type[Any]) -> dict[str, RelatedField]:
    if model is Direction:
        doctor = JoinSpec("direction.doctor", Doctor, Direction.doctor_id == Doctor.id)
        object_ = JoinSpec("direction.object", Object, Direction.object_id == Object.id)
        status = JoinSpec(
            "direction.status",
            DirectionStatus,
            Direction.status_id == DirectionStatus.id,
        )
        return {
            "doctor.name": RelatedField(Doctor.last_name, (doctor,)),
            "object.name": RelatedField(Object.name, (object_,)),
            "status.name": RelatedField(DirectionStatus.name, (status,)),
        }

    if model is Sample:
        sample_type = JoinSpec(
            "sample.sample_type",
            SampleType,
            Sample.sample_type_id == SampleType.id,
        )
        direction = JoinSpec("sample.direction", Direction, Sample.direction_id == Direction.id)
        status = JoinSpec("sample.status", SampleStatus, Sample.status_id == SampleStatus.id)
        return {
            "sample_type.name": RelatedField(SampleType.name, (sample_type,)),
            "direction.name": RelatedField(Direction.id, (direction,)),
            "status.name": RelatedField(SampleStatus.name, (status,)),
        }

    if model is Research:
        sample = JoinSpec("research.sample", Sample, Research.sample_id == Sample.id)
        research_goal = JoinSpec(
            "research.research_goal",
            ResearchGoal,
            Research.research_goal_id == ResearchGoal.id,
        )
        lab = JoinSpec("research.lab", Lab, Research.lab_id == Lab.id)
        status = JoinSpec(
            "research.status",
            ResearchStatus,
            Research.status_id == ResearchStatus.id,
        )
        return {
            "sample.name": RelatedField(Sample.name, (sample,)),
            "research_goal.name": RelatedField(ResearchGoal.name, (research_goal,)),
            "lab.name": RelatedField(Lab.name, (lab,)),
            "status.name": RelatedField(ResearchStatus.name, (status,)),
        }

    if model is Test:
        research = JoinSpec("test.research", Research, Test.research_id == Research.id)
        indicator = JoinSpec("test.indicator", Indicator, Test.indicator_id == Indicator.id)
        status = JoinSpec("test.status", TestStatus, Test.status_id == TestStatus.id)
        return {
            "research.name": RelatedField(Research.id, (research,)),
            "indicator.name": RelatedField(Indicator.name, (indicator,)),
            "status.name": RelatedField(TestStatus.name, (status,)),
        }

    if model is Protocol:
        protocol_type = JoinSpec(
            "protocol.protocol_type",
            ProtocolType,
            Protocol.protocol_type_id == ProtocolType.id,
        )
        conclusion = JoinSpec(
            "protocol.conclusion",
            Conclusion,
            Protocol.conclusion_id == Conclusion.id,
        )
        return {
            "protocol_type.name": RelatedField(ProtocolType.name, (protocol_type,)),
            "conclusion.name": RelatedField(Conclusion.name, (conclusion,)),
        }

    return {}


def _cursor_filter(cursor: CursorState, sort_column: Any, id_column: Any) -> Any:
    sort_value = _coerce_cursor_value(sort_column, cursor.sort_value)
    if cursor.sort_order == "asc":
        return or_(
            sort_column > sort_value,
            and_(sort_column == sort_value, id_column > cursor.item_id),
        )
    return or_(
        sort_column < sort_value,
        and_(sort_column == sort_value, id_column < cursor.item_id),
    )


def _coerce_cursor_value(column: Any, value: Any) -> Any:
    try:
        python_type = column.property.columns[0].type.python_type
    except (AttributeError, NotImplementedError):
        return value
    if python_type is datetime and isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    if python_type is UUID and isinstance(value, str):
        return UUID(value)
    if python_type is int and not isinstance(value, int):
        return int(value)
    return value


def _next_cursor(items: list[Any], sort_by: str, sort_order: str) -> str | None:
    if not items:
        return None
    last = items[-1]
    return encode_cursor(
        sort_by=sort_by,
        sort_order=sort_order,
        sort_value=cursor_sort_value(last, sort_by),
        item_id=getattr(last, "id"),
    )


def _default_sort_field(sortable_fields: tuple[str, ...]) -> str:
    return "created_at" if "created_at" in sortable_fields else "id"


def _pick(values: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: values[field] for field in fields if field in values}


def _direction_sortable_fields() -> tuple[str, ...]:
    return _direction_write_fields() + ("id", "status_id", "created_at", "updated_at")


def _direction_write_fields() -> tuple[str, ...]:
    return (
        "year_no",
        "base_no",
        "is_done",
        "is_urgent",
        "doctor_id",
        "object_id",
        "sampled_at",
        "received_at",
        "completed_at",
        "import_warnings",
    )


def _sample_sortable_fields() -> tuple[str, ...]:
    return _sample_write_fields() + ("id", "status_id", "created_at", "updated_at")


def _sample_write_fields() -> tuple[str, ...]:
    return (
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
        "direction_id",
        "protocol_id",
        "sampled_at",
        "received_at",
        "completed_at",
        "deadline",
        "verdict",
    )


def _research_sortable_fields() -> tuple[str, ...]:
    return _research_write_fields() + ("id", "status_id", "created_at", "updated_at")


def _research_write_fields() -> tuple[str, ...]:
    return (
        "sample_id",
        "research_goal_id",
        "lab_id",
        "comment",
        "recommendation",
        "received_at",
        "completed_at",
    )


def _test_sortable_fields() -> tuple[str, ...]:
    return _test_write_fields() + ("id", "status_id", "created_at", "updated_at")


def _test_write_fields() -> tuple[str, ...]:
    return ("value", "comment", "norm", "is_active", "research_id", "indicator_id")


def _protocol_sortable_fields() -> tuple[str, ...]:
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
