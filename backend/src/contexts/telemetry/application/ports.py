from collections.abc import Iterable
from typing import Protocol

from src.contexts.telemetry.domain.contracts import TelemetryEventDraft


class TelemetryRepository(Protocol):
    async def create_many(self, drafts: Iterable[TelemetryEventDraft]) -> None: ...
