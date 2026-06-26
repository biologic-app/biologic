from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from src.contexts.access_control.infrastructure.repositories import RepositoryPage
from src.core.cursor_pagination import json_value
from src.core.pagination import PageMeta, PaginationParams
from src.core.responses import ListResponse, ResponseMeta, SingleResponse


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
            includes_applied=[],
            includes_allowed=[],
        ),
    )


def single_response(
    item: Any,
    fields: tuple[str, ...],
    *,
    operation: str | None = None,
) -> SingleResponse[dict[str, object]]:
    return SingleResponse(data=serialize(item, fields), meta=ResponseMeta(operation=operation))


def serialize_permission(permission: Any, scope: Any) -> dict[str, object]:
    return {
        "id": json_value(permission.id),
        "resource": permission.resource,
        "action": permission.action,
        "scope": json_value(scope),
    }


def serialize_override(override: Any, permission: Any) -> dict[str, object]:
    return {
        "permission_id": json_value(permission.id),
        "resource": permission.resource,
        "action": permission.action,
        "allowed": override.allowed,
        "scope": json_value(override.scope),
    }


def permission_sort_key(permission: dict[str, object]) -> tuple[str, str, str]:
    return (
        str(permission["resource"]),
        str(permission["action"]),
        str(permission["id"]),
    )
