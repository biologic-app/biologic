from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from src.core.cursor_pagination import json_value
from src.core.pagination import PageMeta, PaginationParams
from src.core.responses import ListResponse, ResponseMeta, SingleResponse
from src.infrastructure.repositories.catalogs import RepositoryPage


def payload_dict(payload: BaseModel) -> dict[str, Any]:
    return payload.model_dump(mode="python", exclude_unset=True)


def serialize(item: Any, fields: tuple[str, ...]) -> dict[str, object]:
    return {field: json_value(getattr(item, field)) for field in fields}


def list_response(
    page: RepositoryPage,
    params: PaginationParams,
    fields: tuple[str, ...],
    allowed_includes: tuple[str, ...] = (),
) -> ListResponse[dict[str, object]]:
    requested = params.includes_requested
    applied = [item for item in requested if item in allowed_includes]
    return ListResponse(
        items=[serialize(item, fields) for item in page.items],
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


def single_response(
    item: Any,
    fields: tuple[str, ...],
    *,
    operation: str | None = None,
) -> SingleResponse[dict[str, object]]:
    return SingleResponse(data=serialize(item, fields), meta=ResponseMeta(operation=operation))
