from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class DomainEvent:
    entity_type: str
    entity_id: UUID
    event_type: str


@dataclass(frozen=True)
class StatusChanged(DomainEvent):
    from_code: str
    to_code: str
    reason: str
