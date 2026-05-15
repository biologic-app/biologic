from typing import Protocol
from uuid import UUID


class PermissionChecker(Protocol):
    async def ensure_allowed(
        self,
        *,
        actor_id: UUID,
        permission: str,
        entity_id: UUID | None = None,
    ) -> None: ...
