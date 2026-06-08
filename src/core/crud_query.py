from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Text, and_, cast

from src.core.errors import BadRequestError
from src.core.global_search import build_global_search_filter
from src.core.pagination import PaginationParams


@dataclass(frozen=True)
class JoinSpec:
    key: str
    model: type[Any]
    on_clause: Any


@dataclass(frozen=True)
class RelatedField:
    column: Any
    joins: tuple[JoinSpec, ...]


@dataclass(frozen=True)
class CrudQueryParts:
    sort_by: str
    sort_column: Any
    filters: list[Any]
    joins: tuple[JoinSpec, ...]


RelatedFields = dict[str, RelatedField]


def build_crud_query_parts(
    *,
    model: type[Any],
    params: PaginationParams,
    sortable_fields: tuple[str, ...],
    base_filters: list[Any],
    related_fields: RelatedFields | None = None,
) -> CrudQueryParts:
    related = related_fields or {}
    sort_by = params.sort_by or _default_sort_field(sortable_fields)
    sort_column, sort_joins = _resolve_sort_field(model, sort_by, sortable_fields, related)
    filters = list(base_filters)
    joins = list(sort_joins)

    filter_predicates, filter_joins = _build_column_filters(model, params.filters, related)
    filters.extend(filter_predicates)
    joins = _merge_joins(joins, filter_joins)

    search_filter = build_global_search_filter(
        model,
        params.search,
        extra_columns=_search_columns(related),
    )
    if search_filter is not None:
        filters.append(search_filter)
        joins = _merge_joins(joins, _search_joins(related))

    return CrudQueryParts(
        sort_by=sort_by,
        sort_column=sort_column,
        filters=filters,
        joins=tuple(joins),
    )


def apply_outer_joins(statement: Any, joins: tuple[JoinSpec, ...]) -> Any:
    for join in joins:
        statement = statement.outerjoin(join.model, join.on_clause)
    return statement


def attach_sort_values(rows: list[tuple[Any, Any]]) -> list[Any]:
    items = []
    for item, sort_value in rows:
        setattr(item, "_crud_sort_value", sort_value)
        items.append(item)
    return items


def cursor_sort_value(item: Any, sort_by: str) -> Any:
    if hasattr(item, "_crud_sort_value"):
        return getattr(item, "_crud_sort_value")
    return getattr(item, sort_by)


def _resolve_sort_field(
    model: type[Any],
    sort_by: str,
    sortable_fields: tuple[str, ...],
    related_fields: RelatedFields,
) -> tuple[Any, tuple[JoinSpec, ...]]:
    if sort_by in sortable_fields:
        return getattr(model, sort_by), ()
    if sort_by in related_fields:
        field = related_fields[sort_by]
        return field.column, field.joins
    raise BadRequestError(f"Unsupported sort field {sort_by!r}.")


def _resolve_filter_field(
    model: type[Any],
    field_name: str,
    related_fields: RelatedFields,
) -> tuple[Any, tuple[JoinSpec, ...]]:
    if "." not in field_name and hasattr(model, field_name):
        return getattr(model, field_name), ()
    if field_name in related_fields:
        field = related_fields[field_name]
        return field.column, field.joins
    raise BadRequestError(f"Unsupported filter field {field_name!r}.")


def _build_column_filters(
    model: type[Any],
    filters_json: str | None,
    related_fields: RelatedFields,
) -> tuple[list[Any], list[JoinSpec]]:
    if not filters_json:
        return [], []
    try:
        raw_filters = json.loads(filters_json)
    except json.JSONDecodeError as exc:
        raise BadRequestError("Invalid filters JSON.") from exc
    if not isinstance(raw_filters, dict):
        raise BadRequestError("Filters must be a JSON object.")

    predicates: list[Any] = []
    joins: list[JoinSpec] = []
    for field_name, value in raw_filters.items():
        column, field_joins = _resolve_filter_field(model, field_name, related_fields)
        predicate = _build_filter_predicate(column, value)
        if predicate is None:
            continue
        predicates.append(predicate)
        joins = _merge_joins(joins, field_joins)
    return predicates, joins


def _build_filter_predicate(column: Any, value: Any) -> Any | None:
    python_type = _python_type(column)

    if isinstance(value, list):
        values = [item for item in value if item not in (None, "")]
        if not values:
            return None
        if len(value) == 2 and python_type in {date, datetime}:
            lower, upper = value
            bounds = []
            if lower not in (None, ""):
                bounds.append(column >= _coerce_filter_bound(python_type, lower, is_upper=False))
            if upper not in (None, ""):
                bounds.append(column <= _coerce_filter_bound(python_type, upper, is_upper=True))
            return and_(*bounds) if bounds else None
        if python_type is UUID:
            return column.in_([_coerce_uuid_filter_value(item) for item in values])
        return column.in_(values)

    if value in (None, ""):
        return None

    if python_type is bool and isinstance(value, bool):
        return column.is_(value)
    if python_type is str:
        return column.ilike(f"%{value}%")
    if python_type is UUID and isinstance(value, str):
        return column == _coerce_uuid_filter_value(value)
    if python_type in {int, float, Decimal, date, datetime} and isinstance(value, str):
        return cast(column, Text).ilike(f"%{value}%")
    return column == value


def _coerce_filter_bound(python_type: type[Any] | None, value: Any, *, is_upper: bool) -> Any:
    if not isinstance(value, str):
        return value

    if python_type is date:
        return date.fromisoformat(value[:10])

    if python_type is datetime:
        if "T" in value:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)

        parsed_date = date.fromisoformat(value[:10])
        bound_time = time.max if is_upper else time.min
        return datetime.combine(parsed_date, bound_time, tzinfo=UTC)

    return value


def _coerce_uuid_filter_value(value: Any) -> Any:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError as exc:
            raise BadRequestError(f"Invalid UUID filter value {value!r}.") from exc
    return value


def _search_columns(related_fields: RelatedFields) -> tuple[Any, ...]:
    columns: list[Any] = []
    for field in related_fields.values():
        if field.column not in columns:
            columns.append(field.column)
    return tuple(columns)


def _search_joins(related_fields: RelatedFields) -> list[JoinSpec]:
    joins: list[JoinSpec] = []
    for field in related_fields.values():
        joins = _merge_joins(joins, field.joins)
    return joins


def _merge_joins(
    left: list[JoinSpec],
    right: tuple[JoinSpec, ...] | list[JoinSpec],
) -> list[JoinSpec]:
    result = list(left)
    existing = {join.key for join in result}
    for join in right:
        if join.key in existing:
            continue
        result.append(join)
        existing.add(join.key)
    return result


def _python_type(column: Any) -> type[Any] | None:
    try:
        return column.property.columns[0].type.python_type
    except (AttributeError, NotImplementedError):
        try:
            return column.type.python_type
        except (AttributeError, NotImplementedError):
            return None


def _default_sort_field(sortable_fields: tuple[str, ...]) -> str:
    if "created_at" in sortable_fields:
        return "created_at"
    if "id" in sortable_fields:
        return "id"
    return sortable_fields[0]
