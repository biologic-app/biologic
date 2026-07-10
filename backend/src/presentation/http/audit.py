from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.cursor_pagination import json_value
from src.core.database import get_db_session
from src.core.pagination import PageMeta, PaginationDependency, PaginationParams
from src.core.responses import ListResponse, ResponseMeta, SingleResponse
from src.infrastructure.db.models import ChangeLog, User
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
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ListResponse[dict[str, object]]:
    page = await repository.list(params)
    actor_names = await _resolve_actor_names(session, page.items)
    return ListResponse(
        items=[_serialize_history(row, actor_names) for row in page.items],
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
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SingleResponse[dict[str, object]]:
    row = await repository.read(history_id)
    actor_names = await _resolve_actor_names(session, [row])
    return SingleResponse(
        data=_serialize_history(row, actor_names),
        meta=ResponseMeta(),
    )


def _short_person_name(
    last_name: str | None, first_name: str | None, patronymic: str | None, username: str
) -> str:
    """«Фамилия И.О.» — как принято в протоколах; fallback на username."""
    initials = "".join(
        f"{part.strip()[0].upper()}." for part in (first_name, patronymic) if part and part.strip()
    )
    last = (last_name or "").strip()
    return " ".join(filter(None, [last, initials])) or username


async def _resolve_actor_names(
    session: AsyncSession, rows: list[ChangeLog]
) -> dict[UUID, str]:
    """Читаемое имя актора по actor_id: transitions пишут только UUID,
    а UI обязан показывать, кто перевёл запись в статус."""
    actor_ids = {row.actor_id for row in rows if row.actor_id is not None}
    if not actor_ids:
        return {}
    result = await session.execute(
        select(
            User.id, User.username, User.first_name, User.last_name, User.patronymic
        ).where(User.id.in_(actor_ids))
    )
    return {
        user_id: _short_person_name(last_name, first_name, patronymic, username)
        for user_id, username, first_name, last_name, patronymic in result.all()
    }


def _serialize_history(
    row: ChangeLog, actor_names: dict[UUID, str] | None = None
) -> dict[str, object]:
    resolved = (
        (actor_names or {}).get(row.actor_id) if row.actor_id is not None else None
    )
    return {
        "id": json_value(row.id),
        "branch_id": json_value(row.branch_id),
        "entity_type": row.entity_type,
        "entity_id": json_value(row.entity_id),
        "action": row.action,
        "actor_id": json_value(row.actor_id),
        "actor_name": resolved or row.actor_name,
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
