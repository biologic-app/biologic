from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, asc, delete, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.cursor_pagination import CursorState, decode_cursor, encode_cursor
from src.core.errors import BadRequestError, DomainConflictError, NotFoundError
from src.core.pagination import PaginationParams
from src.infrastructure.db.models import (
    Direction,
    Lab,
    Protocol,
    Research,
    ResearchGoal,
    ResearchStatus,
    Sample,
    Test,
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
        return await _list_rows(
            self.session, Direction, params, _direction_sortable_fields()
        )

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
        )

    async def delete(self, direction_id: UUID) -> None:
        await _delete_row(self.session, await self.read(direction_id))


class SampleCrudRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        return await _list_rows(self.session, Sample, params, _sample_sortable_fields())

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
        )

    async def delete(self, research_id: UUID) -> None:
        await _delete_row(self.session, await self.read(research_id))


class TestCrudRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        return await _list_rows(self.session, Test, params, _test_sortable_fields())

    async def read(self, test_id: UUID) -> Any:
        return await _read_row(self.session, Test, "tests", test_id)

    async def update(self, test_id: UUID, values: dict[str, Any]) -> Any:
        _reject_status_update("tests", values)
        return await _update_row(
            self.session,
            await self.read(test_id),
            _pick(values, _test_write_fields()),
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
    sort_by = params.sort_by or _default_sort_field(sortable_fields)
    if sort_by not in sortable_fields:
        raise BadRequestError(f"Unsupported sort field {sort_by!r}.")
    sort_column = getattr(model, sort_by)
    id_column = getattr(model, "id")
    filters = _base_filters(model)
    cursor = decode_cursor(params.cursor) if params.cursor else None
    if cursor is not None:
        if cursor.sort_by != sort_by or cursor.sort_order != params.sort_order:
            raise BadRequestError("Pagination cursor does not match requested sorting.")
        filters.append(_cursor_filter(cursor, model, sort_column, id_column))

    total_result = await session.execute(
        select(func.count()).select_from(model).where(*_base_filters(model)),
    )
    total = int(total_result.scalar_one())
    order_fn = asc if params.sort_order == "asc" else desc
    query = (
        select(model)
        .where(*filters)
        .order_by(order_fn(sort_column), order_fn(id_column))
        .limit(params.limit + 1)
    )
    result = await session.execute(query)
    rows = list(result.scalars().all())
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


async def _update_row(session: AsyncSession, row: Any, values: dict[str, Any]) -> Any:
    for field, value in values.items():
        setattr(row, field, value)
    if hasattr(row, "updated_at"):
        setattr(row, "updated_at", datetime.now(UTC))
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


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


def _cursor_filter(
    cursor: CursorState, model: type[Any], sort_column: Any, id_column: Any
) -> Any:
    sort_value = _coerce_cursor_value(model, cursor.sort_by, cursor.sort_value)
    if cursor.sort_order == "asc":
        return or_(
            sort_column > sort_value,
            and_(sort_column == sort_value, id_column > cursor.item_id),
        )
    return or_(
        sort_column < sort_value,
        and_(sort_column == sort_value, id_column < cursor.item_id),
    )


def _coerce_cursor_value(model: type[Any], sort_by: str, value: Any) -> Any:
    column = getattr(model, sort_by)
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
        sort_value=getattr(last, sort_by),
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
