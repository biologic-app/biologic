import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors import BadRequestError, NotFoundError
from src.core.pagination import PaginationParams
from src.infrastructure.db.models import ChangeLog


@dataclass(frozen=True)
class AuditRepositoryPage:
    items: list[ChangeLog]
    total: int
    has_more: bool
    next_cursor: str | None = None


class ChangeLogAuditRepository:
    """Expose the legacy change_log table as the MVP history writer."""

    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def list(self, params: PaginationParams) -> AuditRepositoryPage:
        filters = _history_filters(params.filters)
        total_result = await self.session.execute(
            select(func.count()).select_from(ChangeLog).where(*filters),
        )
        total = int(total_result.scalar_one())
        result = await self.session.execute(
            select(ChangeLog)
            .where(*filters)
            .order_by(desc(ChangeLog.created_at), desc(ChangeLog.id))
            .limit(params.limit + 1),
        )
        rows = list(result.scalars().all())
        return AuditRepositoryPage(
            items=rows[: params.limit],
            total=total,
            has_more=len(rows) > params.limit,
        )

    async def read(self, history_id: UUID) -> ChangeLog:
        result = await self.session.execute(
            select(ChangeLog).where(ChangeLog.id == history_id),
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundError(f"history item {history_id} was not found.")
        return row

    async def write(
        self,
        *,
        entity_type: str,
        entity_id: UUID,
        action: str,
        actor_id: UUID,
        snapshot: dict[str, Any] | None,
        diff: dict[str, Any] | None,
    ) -> None:
        self.session.add(
            ChangeLog(
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                actor_id=actor_id,
                snapshot=snapshot,
                diff=diff,
            ),
        )


def _history_filters(filters_json: str | None) -> list[Any]:
    if not filters_json:
        return []
    try:
        raw_filters = json.loads(filters_json)
    except json.JSONDecodeError as exc:
        raise BadRequestError("Invalid filters JSON.") from exc
    if not isinstance(raw_filters, dict):
        raise BadRequestError("Filters must be a JSON object.")

    predicates: list[Any] = []
    for field, value in raw_filters.items():
        if value in (None, ""):
            continue
        if field == "entity_type":
            predicates.append(ChangeLog.entity_type == str(value))
            continue
        if field == "entity_id":
            predicates.append(ChangeLog.entity_id == _uuid_filter_value(value))
            continue
        if field == "action":
            predicates.append(ChangeLog.action == str(value))
            continue
        raise BadRequestError(f"Unsupported filter field {field!r}.")
    return predicates


def _uuid_filter_value(value: Any) -> UUID:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError as exc:
            raise BadRequestError(f"Invalid UUID filter value {value!r}.") from exc
    raise BadRequestError(f"Invalid UUID filter value {value!r}.")
