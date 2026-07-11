from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.telemetry.domain.contracts import TelemetryEventDraft
from src.infrastructure.db.models import UiEvent


class SqlAlchemyTelemetryRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def create_many(self, drafts: Iterable[TelemetryEventDraft]) -> None:
        rows = [
            UiEvent(
                event=draft.event,
                element_id=draft.element_id,
                route=draft.route,
                role=draft.role,
                session_id=draft.session_id,
                ts=draft.ts,
            )
            for draft in drafts
        ]
        if not rows:
            return
        self.session.add_all(rows)
        await self.session.commit()
