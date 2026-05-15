from uuid import UUID

from pydantic import BaseModel


class RegisterDirectionRequest(BaseModel):
    actor_id: UUID
    comment: str | None = None
