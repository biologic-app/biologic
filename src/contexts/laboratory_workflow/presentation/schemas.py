from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator


class RegisterDirectionRequest(BaseModel):
    actor_id: UUID
    comment: str | None = None


class RegisterSampleRequest(BaseModel):
    actor_id: UUID
    received_at: datetime
    deadline: datetime | None = None

    @field_validator("received_at", "deadline")
    @classmethod
    def require_aware_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            msg = "timestamp must be timezone-aware"
            raise ValueError(msg)
        return value
