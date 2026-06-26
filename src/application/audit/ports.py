from typing import Any, Protocol
from uuid import UUID


class AuditWriter(Protocol):
    async def write(
        self,
        *,
        entity_type: str,
        entity_id: UUID,
        action: str,
        actor_id: UUID,
        snapshot: dict[str, Any] | None,
        diff: dict[str, Any] | None,
    ) -> None: ...
