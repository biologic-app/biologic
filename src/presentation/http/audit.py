from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.cursor_pagination import json_value
from src.core.database import get_db_session
from src.core.pagination import PageMeta, PaginationDependency, PaginationParams
from src.core.responses import ListResponse, ResponseMeta, SingleResponse
from src.infrastructure.db.models import ChangeLog
from src.infrastructure.repositories.audit import ChangeLogAuditRepository

router = APIRouter(tags=["audit"])


async def get_audit_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ChangeLogAuditRepository:
    return ChangeLogAuditRepository(session=session)


def _meta(
    params: PaginationParams,
    *,
    total: int,
    has_more: bool,
    next_cursor: str | None = None,
) -> PageMeta:
    return PageMeta(
        total=total,
        limit=params.limit,
        next_cursor=next_cursor,
        has_more=has_more,
        includes_requested=params.includes_requested,
        includes_applied=[],
        includes_allowed=[],
    )


@router.get("/history")
async def list_history(
    params: PaginationDependency,
    repository: Annotated[ChangeLogAuditRepository, Depends(get_audit_repository)],
) -> ListResponse[dict[str, object]]:
    page = await repository.list(params)
    return ListResponse(
        items=[_serialize_history(row) for row in page.items],
        meta=_meta(
            params,
            total=page.total,
            has_more=page.has_more,
            next_cursor=page.next_cursor,
        ),
    )


@router.get("/history/{history_id}")
async def read_history(
    history_id: UUID,
    repository: Annotated[ChangeLogAuditRepository, Depends(get_audit_repository)],
) -> SingleResponse[dict[str, object]]:
    return SingleResponse(
        data=_serialize_history(await repository.read(history_id)),
        meta=ResponseMeta(),
    )


def _serialize_history(row: ChangeLog) -> dict[str, object]:
    return {
        "id": json_value(row.id),
        "branch_id": json_value(row.branch_id),
        "entity_type": row.entity_type,
        "entity_id": json_value(row.entity_id),
        "action": row.action,
        "actor_id": json_value(row.actor_id),
        "actor_name": row.actor_name,
        "snapshot": _json_value(row.snapshot),
        "diff": _json_value(row.diff),
        "created_at": json_value(row.created_at),
    }


def _json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return json_value(value)
