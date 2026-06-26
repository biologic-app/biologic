from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class HistoryEntry:
    entity_type: str
    entity_id: UUID
    action: str
    actor_id: UUID
    snapshot: dict[str, Any] | None
    diff: dict[str, Any] | None
