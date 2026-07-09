from __future__ import annotations

from collections.abc import Sequence
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
from src.core.cursor_pagination import CursorState, decode_cursor, encode_cursor
from src.core.errors import BadRequestError, DomainConflictError, NotFoundError
from src.core.pagination import PaginationParams
from src.infrastructure.db.models import (
    Branch,
    Conclusion,
    DirectionStatus,
    Doctor,
    Indicator,
    Lab,
    Object,
    ProtocolType,
    ResearchGoal,
    ResearchStatus,
    SampleStatus,
    SampleType,
    TestStatus,
)


@dataclass(frozen=True)
class RepositoryPage:
    items: list[Any]
    total: int
    has_more: bool
    next_cursor: str | None


class BranchRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        return await _list_rows(self.session, Branch, params, _branch_sortable_fields())

    async def read(self, item_id: UUID) -> Any:
        return await _read_row(self.session, Branch, "branches", item_id)

    async def create(self, values: dict[str, Any]) -> Any:
        return await _create_row(self.session, Branch, _pick(values, ("code", "name")))

    async def update(self, item_id: UUID, values: dict[str, Any]) -> Any:
        row = await self.read(item_id)
        return await _update_row(self.session, row, _pick(values, ("code", "name")))

    async def delete(self, item_id: UUID) -> None:
        await _delete_row(self.session, await self.read(item_id))


class LabRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        return await _list_rows(self.session, Lab, params, _lab_sortable_fields())

    async def read(self, item_id: UUID) -> Any:
        return await _read_row(self.session, Lab, "labs", item_id)

    async def create(self, values: dict[str, Any]) -> Any:
        return await _create_row(
            self.session,
            Lab,
            _pick(values, ("branch_id", "code", "name", "full_name")),
        )

    async def update(self, item_id: UUID, values: dict[str, Any]) -> Any:
        row = await self.read(item_id)
        return await _update_row(
            self.session,
            row,
            _pick(values, ("branch_id", "code", "name", "full_name")),
        )

    async def delete(self, item_id: UUID) -> None:
        await _delete_row(self.session, await self.read(item_id))


class ObjectRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        return await _list_rows(self.session, Object, params, _object_sortable_fields())

    async def read(self, item_id: UUID) -> Any:
        return await _read_row(self.session, Object, "objects", item_id)

    async def find_by_name(self, name: str) -> Sequence[Any]:
        cleaned = name.strip()
        if not cleaned:
            return []
        cleaned_lower = cleaned.lower()
        result = await self.session.execute(
            select(Object).where(
                Object.deleted_at.is_(None),
                or_(
                    func.lower(func.trim(Object.name)) == cleaned_lower,
                    func.lower(func.trim(Object.full_name)) == cleaned_lower,
                ),
            )
        )
        return list(result.scalars().all())

    async def create(self, values: dict[str, Any]) -> Any:
        return await _create_row(
            self.session,
            Object,
            _pick(values, ("branch_id", "code", "name", "full_name", "address")),
        )

    async def update(self, item_id: UUID, values: dict[str, Any]) -> Any:
        row = await self.read(item_id)
        return await _update_row(
            self.session,
            row,
            _pick(values, ("branch_id", "code", "name", "full_name", "address")),
        )

    async def delete(self, item_id: UUID) -> None:
        await _delete_row(self.session, await self.read(item_id))


class DoctorRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        return await _list_rows(self.session, Doctor, params, _doctor_sortable_fields())

    async def read(self, item_id: UUID) -> Any:
        return await _read_row(self.session, Doctor, "doctors", item_id)

    async def find_by_last_name(self, last_name: str) -> Sequence[Any]:
        cleaned = last_name.strip()
        if not cleaned:
            return []
        result = await self.session.execute(
            select(Doctor).where(
                Doctor.deleted_at.is_(None),
                func.lower(func.trim(Doctor.last_name)) == cleaned.lower(),
            )
        )
        return list(result.scalars().all())

    async def create(self, values: dict[str, Any]) -> Any:
        return await _create_row(
            self.session,
            Doctor,
            _pick(values, ("first_name", "last_name", "patronymic")),
        )

    async def update(self, item_id: UUID, values: dict[str, Any]) -> Any:
        row = await self.read(item_id)
        return await _update_row(
            self.session,
            row,
            _pick(values, ("first_name", "last_name", "patronymic")),
        )

    async def delete(self, item_id: UUID) -> None:
        await _delete_row(self.session, await self.read(item_id))


class SampleTypeRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        return await _list_rows(self.session, SampleType, params, _sample_type_sortable_fields())

    async def read(self, item_id: UUID) -> Any:
        return await _read_row(self.session, SampleType, "sample_types", item_id)

    async def create(self, values: dict[str, Any]) -> Any:
        return await _create_row(self.session, SampleType, _pick(values, ("code", "name")))

    async def update(self, item_id: UUID, values: dict[str, Any]) -> Any:
        row = await self.read(item_id)
        return await _update_row(self.session, row, _pick(values, ("code", "name")))

    async def delete(self, item_id: UUID) -> None:
        await _delete_row(self.session, await self.read(item_id))


class ResearchGoalRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        return await _list_rows(
            self.session,
            ResearchGoal,
            params,
            _research_goal_sortable_fields(),
        )

    async def read(self, item_id: UUID) -> Any:
        return await _read_row(self.session, ResearchGoal, "research_goals", item_id)

    async def create(self, values: dict[str, Any]) -> Any:
        return await _create_row(
            self.session,
            ResearchGoal,
            _pick(values, ("code", "name", "comment", "lab_id")),
        )

    async def update(self, item_id: UUID, values: dict[str, Any]) -> Any:
        row = await self.read(item_id)
        return await _update_row(
            self.session,
            row,
            _pick(values, ("code", "name", "comment", "lab_id")),
        )

    async def delete(self, item_id: UUID) -> None:
        await _delete_row(self.session, await self.read(item_id))


class IndicatorRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        return await _list_rows(self.session, Indicator, params, _indicator_sortable_fields())

    async def read(self, item_id: UUID) -> Any:
        return await _read_row(self.session, Indicator, "indicators", item_id)

    async def create(self, values: dict[str, Any]) -> Any:
        return await _create_row(self.session, Indicator, _pick(values, _indicator_write_fields()))

    async def update(self, item_id: UUID, values: dict[str, Any]) -> Any:
        row = await self.read(item_id)
        return await _update_row(self.session, row, _pick(values, _indicator_write_fields()))

    async def delete(self, item_id: UUID) -> None:
        await _delete_row(self.session, await self.read(item_id))


class ConclusionRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        return await _list_rows(self.session, Conclusion, params, _conclusion_sortable_fields())

    async def read(self, item_id: UUID) -> Any:
        return await _read_row(self.session, Conclusion, "conclusions", item_id)

    async def create(self, values: dict[str, Any]) -> Any:
        return await _create_row(
            self.session,
            Conclusion,
            _pick(values, _conclusion_write_fields()),
        )

    async def update(self, item_id: UUID, values: dict[str, Any]) -> Any:
        row = await self.read(item_id)
        return await _update_row(self.session, row, _pick(values, _conclusion_write_fields()))

    async def delete(self, item_id: UUID) -> None:
        await _delete_row(self.session, await self.read(item_id))


class ProtocolTypeRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        return await _list_rows(
            self.session,
            ProtocolType,
            params,
            _protocol_type_sortable_fields(),
        )

    async def read(self, item_id: UUID) -> Any:
        return await _read_row(self.session, ProtocolType, "protocol_types", item_id)

    async def create(self, values: dict[str, Any]) -> Any:
        return await _create_row(self.session, ProtocolType, _pick(values, ("code", "name")))

    async def update(self, item_id: UUID, values: dict[str, Any]) -> Any:
        row = await self.read(item_id)
        return await _update_row(self.session, row, _pick(values, ("code", "name")))

    async def delete(self, item_id: UUID) -> None:
        await _delete_row(self.session, await self.read(item_id))


class DirectionStatusRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        return await _list_rows(
            self.session,
            DirectionStatus,
            params,
            _status_sortable_fields(),
        )

    async def read(self, item_id: UUID) -> Any:
        return await _read_row(self.session, DirectionStatus, "direction_statuses", item_id)

    async def update(self, item_id: UUID, values: dict[str, Any]) -> Any:
        row = await self.read(item_id)
        return await _update_row(self.session, row, _pick(values, ("name",)))


class SampleStatusRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        return await _list_rows(self.session, SampleStatus, params, _status_sortable_fields())

    async def read(self, item_id: UUID) -> Any:
        return await _read_row(self.session, SampleStatus, "sample_statuses", item_id)

    async def update(self, item_id: UUID, values: dict[str, Any]) -> Any:
        row = await self.read(item_id)
        return await _update_row(self.session, row, _pick(values, ("name",)))


class ResearchStatusRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        return await _list_rows(self.session, ResearchStatus, params, _status_sortable_fields())

    async def read(self, item_id: UUID) -> Any:
        return await _read_row(self.session, ResearchStatus, "research_statuses", item_id)

    async def update(self, item_id: UUID, values: dict[str, Any]) -> Any:
        row = await self.read(item_id)
        return await _update_row(self.session, row, _pick(values, ("name",)))


class TestStatusRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> RepositoryPage:
        return await _list_rows(self.session, TestStatus, params, _status_sortable_fields())

    async def read(self, item_id: UUID) -> Any:
        return await _read_row(self.session, TestStatus, "test_statuses", item_id)

    async def update(self, item_id: UUID, values: dict[str, Any]) -> Any:
        row = await self.read(item_id)
        return await _update_row(self.session, row, _pick(values, ("name",)))


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
    return RepositoryPage(items=items, total=total, has_more=has_more, next_cursor=next_cursor)


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


async def _create_row(session: AsyncSession, model: type[Any], values: dict[str, Any]) -> Any:
    row = model(**values)
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def _update_row(session: AsyncSession, row: Any, values: dict[str, Any]) -> Any:
    for field, value in values.items():
        setattr(row, field, value)
    if hasattr(row, "updated_at"):
        setattr(row, "updated_at", datetime.now(UTC))
    session.add(row)
    await session.flush()
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
    await session.flush()


def reject_status_write(resource: str) -> None:
    raise DomainConflictError(
        code="resource_read_only",
        detail=f"{resource} cannot be changed through catalog CRUD.",
    )


def _base_filters(model: type[Any]) -> list[Any]:
    if hasattr(model, "deleted_at"):
        return [getattr(model, "deleted_at").is_(None)]
    return []


def _related_fields(model: type[Any]) -> dict[str, RelatedField]:
    if model is Lab:
        branch = JoinSpec("lab.branch", Branch, Lab.branch_id == Branch.id)
        return {"branch.name": RelatedField(Branch.name, (branch,))}

    if model is Object:
        branch = JoinSpec("object.branch", Branch, Object.branch_id == Branch.id)
        return {"branch.name": RelatedField(Branch.name, (branch,))}

    if model is ResearchGoal:
        lab = JoinSpec("research_goal.lab", Lab, ResearchGoal.lab_id == Lab.id)
        return {"lab.name": RelatedField(Lab.name, (lab,))}

    if model is Indicator:
        research_goal = JoinSpec(
            "indicator.research_goal",
            ResearchGoal,
            Indicator.research_goal_id == ResearchGoal.id,
        )
        lab = JoinSpec("indicator.lab", Lab, ResearchGoal.lab_id == Lab.id)
        sample_type = JoinSpec(
            "indicator.sample_type",
            SampleType,
            Indicator.sample_type_id == SampleType.id,
        )
        return {
            "research_goal.name": RelatedField(ResearchGoal.name, (research_goal,)),
            "lab.name": RelatedField(Lab.name, (research_goal, lab)),
            "sample_type.name": RelatedField(SampleType.name, (sample_type,)),
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
    if "created_at" in sortable_fields:
        return "created_at"
    if "id" in sortable_fields:
        return "id"
    return sortable_fields[0]


def _pick(values: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: values[field] for field in fields if field in values}


def _branch_sortable_fields() -> tuple[str, ...]:
    return ("id", "code", "name", "created_at", "updated_at")


def _lab_sortable_fields() -> tuple[str, ...]:
    return ("id", "branch_id", "code", "name", "full_name", "created_at", "updated_at")


def _object_sortable_fields() -> tuple[str, ...]:
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


def _doctor_sortable_fields() -> tuple[str, ...]:
    return ("id", "first_name", "last_name", "patronymic", "created_at", "updated_at")


def _sample_type_sortable_fields() -> tuple[str, ...]:
    return ("id", "code", "name", "created_at", "updated_at")


def _research_goal_sortable_fields() -> tuple[str, ...]:
    return ("id", "code", "name", "comment", "lab_id", "created_at", "updated_at")


def _indicator_sortable_fields() -> tuple[str, ...]:
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


def _indicator_write_fields() -> tuple[str, ...]:
    return (
        "name",
        "unit",
        "norm_text",
        "norm_value",
        "default_text",
        "comment",
        "research_goal_id",
        "sample_type_id",
    )


def _conclusion_sortable_fields() -> tuple[str, ...]:
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


def _conclusion_write_fields() -> tuple[str, ...]:
    return ("code", "name", "text_singular", "text_plural", "comment")


def _protocol_type_sortable_fields() -> tuple[str, ...]:
    return ("id", "code", "name", "created_at", "updated_at")


def _status_sortable_fields() -> tuple[str, ...]:
    return ("id", "code", "name", "created_at", "updated_at")
