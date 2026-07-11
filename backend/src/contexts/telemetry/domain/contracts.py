from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TelemetryEventDraft:
    """A single passive UI telemetry event awaiting persistence.

    Anonymous by design — only identifiers are carried, never form values or
    other user-entered content (ROADMAP A2.3).
    """

    event: str
    route: str
    session_id: str
    ts: datetime
    element_id: str | None = None
    role: str | None = None
