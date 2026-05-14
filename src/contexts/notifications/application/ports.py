from typing import Protocol
from uuid import UUID


class AlertWriter(Protocol):
    async def create_alert(
        self,
        *,
        user_id: UUID,
        branch_id: UUID | None,
        entity_type: str,
        entity_id: UUID,
        alert_type: str,
        message: str,
    ) -> None: ...
