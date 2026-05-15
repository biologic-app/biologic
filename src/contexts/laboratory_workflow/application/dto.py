from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator


class CommandResult(BaseModel):
    id: UUID
    status_id: UUID
    updated_at: datetime

    @field_validator("updated_at")
    @classmethod
    def require_aware_updated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            msg = "updated_at must be timezone-aware"
            raise ValueError(msg)
        return value


class RegisterDirectionInput(BaseModel):
    direction_id: UUID
    actor_id: UUID
    comment: str | None = None


class RegisterSampleInput(BaseModel):
    sample_id: UUID
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


class RejectSampleInput(BaseModel):
    sample_id: UUID
    actor_id: UUID
    reason: str


class AssignResearchInput(BaseModel):
    sample_id: UUID
    actor_id: UUID
    research_goal_id: UUID
    comment: str | None = None


class CompleteTestInput(BaseModel):
    test_id: UUID
    actor_id: UUID
    value: str
    norm: str | None = None
    comment: str | None = None
