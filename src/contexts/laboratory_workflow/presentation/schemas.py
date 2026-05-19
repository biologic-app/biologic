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


class RejectSampleRequest(BaseModel):
    actor_id: UUID
    reason: str


class ActorRequest(BaseModel):
    actor_id: UUID


class AssignResearchRequest(BaseModel):
    actor_id: UUID
    research_goal_id: UUID
    comment: str | None = None


class CompleteTestRequest(BaseModel):
    actor_id: UUID
    value: str
    norm: str | None = None
    comment: str | None = None


class RejectTestRequest(BaseModel):
    actor_id: UUID
    reason: str


class CloseSampleRequest(BaseModel):
    actor_id: UUID
    verdict: str
    comment: str | None = None


class CreateProtocolRequest(BaseModel):
    actor_id: UUID
    sample_ids: list[UUID]
    protocol_type_id: UUID | None = None
    conclusion_id: UUID | None = None
    copies: int | None = None


class UpdateProtocolRequest(BaseModel):
    actor_id: UUID
    protocol_type_id: UUID | None = None
    conclusion_id: UUID | None = None
    copies: int | None = None


class IssueProtocolRequest(BaseModel):
    actor_id: UUID
    issued_at: datetime | None = None

    @field_validator("issued_at")
    @classmethod
    def require_aware_issued_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            msg = "timestamp must be timezone-aware"
            raise ValueError(msg)
        return value
