from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DirectionCreateRequest(StrictRequest):
    year_no: int
    base_no: int | None = None
    is_done: bool | None = None
    is_urgent: bool | None = None
    doctor_id: UUID | None = None
    object_id: UUID | None = None
    sampled_at: datetime | None = None
    received_at: datetime | None = None
    completed_at: datetime | None = None
    import_warnings: dict[str, object] | None = None


class DirectionUpdateRequest(StrictRequest):
    year_no: int | None = None
    base_no: int | None = None
    is_done: bool | None = None
    is_urgent: bool | None = None
    doctor_id: UUID | None = None
    object_id: UUID | None = None
    sampled_at: datetime | None = None
    received_at: datetime | None = None
    completed_at: datetime | None = None
    import_warnings: dict[str, object] | None = None
    status_id: UUID | None = None


class SampleCreateRequest(StrictRequest):
    month_no: int | None = None
    name: str
    alternate_name: str | None = None
    mass: str | None = None
    target_description: str | None = None
    comment: str | None = None
    section: str | None = None
    delivery: str | None = None
    nomenclature_code: str | None = None
    batch_code: str | None = None
    supplier: str | None = None
    is_urgent: bool | None = None
    is_done: bool | None = None
    sample_type_id: UUID | None = None
    direction_id: UUID | None = None
    protocol_id: UUID | None = None
    sampled_at: datetime | None = None
    received_at: datetime | None = None
    completed_at: datetime | None = None
    deadline: datetime | None = None
    verdict: str | None = None


class SampleUpdateRequest(StrictRequest):
    month_no: int | None = None
    name: str | None = None
    alternate_name: str | None = None
    mass: str | None = None
    target_description: str | None = None
    comment: str | None = None
    section: str | None = None
    delivery: str | None = None
    nomenclature_code: str | None = None
    batch_code: str | None = None
    supplier: str | None = None
    is_urgent: bool | None = None
    is_done: bool | None = None
    sample_type_id: UUID | None = None
    direction_id: UUID | None = None
    protocol_id: UUID | None = None
    sampled_at: datetime | None = None
    received_at: datetime | None = None
    completed_at: datetime | None = None
    deadline: datetime | None = None
    verdict: str | None = None
    status_id: UUID | None = None


class ResearchUpdateRequest(StrictRequest):
    sample_id: UUID | None = None
    research_goal_id: UUID | None = None
    lab_id: UUID | None = None
    comment: str | None = None
    recommendation: str | None = None
    received_at: datetime | None = None
    completed_at: datetime | None = None
    status_id: UUID | None = None


class TestUpdateRequest(StrictRequest):
    value: str | None = None
    comment: str | None = None
    norm: str | None = None
    is_active: bool | None = None
    research_id: UUID | None = None
    indicator_id: UUID | None = None
    status_id: UUID | None = None


class SampleLabsUpdateRequest(StrictRequest):
    lab_ids: list[UUID]


class SubscriptionRequest(StrictRequest):
    # Явный пользователь; если не задан — берётся текущий из сессии.
    user_id: UUID | None = None


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


class RejectResearchRequest(BaseModel):
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
