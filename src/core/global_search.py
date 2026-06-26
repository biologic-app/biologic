from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Text, cast, or_
from sqlalchemy.inspection import inspect

SENSITIVE_FIELD_MARKERS = ("password", "token", "secret")


def build_global_search_filter(
    model: type[Any],
    search: str | None,
    *,
    extra_columns: tuple[Any, ...] = (),
) -> Any | None:
    term = search.strip() if search else ""
    if not term:
        return None

    pattern = f"%{term}%"
    predicates: list[Any] = []
    columns = [column_property.columns[0] for column_property in inspect(model).column_attrs]
    columns.extend(extra_columns)

    for column in columns:
        field_name = column.key
        if any(marker in field_name for marker in SENSITIVE_FIELD_MARKERS):
            continue

        python_type = _python_type(column)
        if python_type is str:
            predicates.append(column.ilike(pattern))
            continue

        if python_type in {int, float, Decimal, UUID, date, datetime}:
            predicates.append(cast(column, Text).ilike(pattern))

    return or_(*predicates) if predicates else None


def _python_type(column: Any) -> type[Any] | None:
    try:
        col_type: type[Any] = column.type.python_type
        return col_type
    except (AttributeError, NotImplementedError):
        return None
