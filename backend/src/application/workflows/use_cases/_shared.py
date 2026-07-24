from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from src.core.cursor_pagination import json_value
from src.core.pagination import PageMeta, PaginationParams
from src.core.responses import ListResponse, ResponseMeta, SingleResponse
from src.infrastructure.repositories.catalogs import RepositoryPage

TEMPLATE_FIELDS = ("id", "title", "current_version", "created_at", "updated_at")
VERSION_FIELDS = ("id", "template_id", "version", "schema", "created_at")
RUN_FIELDS = (
    "id",
    "template_id",
    "schema_version",
    "scope_kind",
    "scope_id",
    "title",
    "status",
    "answers",
    "loops",
    "history",
    "current_node_id",
    "created_by",
    "created_at",
    "updated_at",
)
EVENT_FIELDS = ("id", "run_id", "kind", "node_id", "payload", "author", "created_at")
ATTACHMENT_FIELDS = (
    "id",
    "run_id",
    "field_id",
    "filename",
    "content_type",
    "size_bytes",
    "storage",
    "created_at",
)


def payload_dict(payload: BaseModel) -> dict[str, Any]:
    return payload.model_dump(mode="python", exclude_unset=True)


def serialize(item: Any, fields: tuple[str, ...]) -> dict[str, object]:
    return {field: json_value(getattr(item, field)) for field in fields}


def list_response(
    page: RepositoryPage,
    params: PaginationParams,
    fields: tuple[str, ...],
) -> ListResponse[dict[str, object]]:
    return ListResponse(
        items=[serialize(item, fields) for item in page.items],
        meta=PageMeta(
            total=page.total,
            limit=params.limit,
            next_cursor=page.next_cursor,
            has_more=page.has_more,
            includes_requested=params.includes_requested,
        ),
    )


def single_response(
    data: dict[str, object],
    *,
    operation: str | None = None,
) -> SingleResponse[dict[str, object]]:
    return SingleResponse(data=data, meta=ResponseMeta(operation=operation))
