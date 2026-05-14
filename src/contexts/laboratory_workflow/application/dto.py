from uuid import UUID

from pydantic import BaseModel


class CommandResult(BaseModel):
    id: UUID
    status_id: UUID
    updated_at: str


class RegisterDirectionInput(BaseModel):
    direction_id: UUID
    actor_id: UUID
    comment: str | None = None


class RegisterSampleInput(BaseModel):
    sample_id: UUID
    actor_id: UUID
    received_at: str
    deadline: str | None = None


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
