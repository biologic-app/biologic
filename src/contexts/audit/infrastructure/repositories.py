from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models import ChangeLog


class ChangeLogAuditRepository:
    """Expose the legacy change_log table as the MVP history writer."""

    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

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
