from __future__ import annotations

import logging
from collections.abc import Iterable

from src.contexts.telemetry.application.ports import TelemetryRepository
from src.contexts.telemetry.domain.contracts import TelemetryEventDraft

logger = logging.getLogger(__name__)


class TelemetryService:
    """Fire-and-forget ingestion: a write failure must never fail the
    request, it is only logged (ROADMAP A2.3 — telemetry is best-effort).
    """

    def __init__(self, *, repository: TelemetryRepository) -> None:
        self.repository = repository

    async def record_events(self, drafts: Iterable[TelemetryEventDraft]) -> int:
        drafts = list(drafts)
        try:
            await self.repository.create_many(drafts)
        except Exception:  # noqa: BLE001 — telemetry must never break the caller
            logger.warning("Failed to persist UI telemetry batch.", exc_info=True)
            return 0
        return len(drafts)
