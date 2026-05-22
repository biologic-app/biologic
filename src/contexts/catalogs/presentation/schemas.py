from uuid import UUID

from pydantic import BaseModel, ConfigDict


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BranchCreateRequest(StrictRequest):
    code: str | None = None
    name: str | None = None


class BranchUpdateRequest(BranchCreateRequest):
    pass


class LabCreateRequest(StrictRequest):
    branch_id: UUID | None = None
    code: str
    name: str
    full_name: str | None = None


class LabUpdateRequest(StrictRequest):
    branch_id: UUID | None = None
    code: str | None = None
    name: str | None = None
    full_name: str | None = None


class ObjectCreateRequest(StrictRequest):
    branch_id: UUID | None = None
    code: str
    name: str
    full_name: str | None = None
    address: str | None = None


class ObjectUpdateRequest(StrictRequest):
    branch_id: UUID | None = None
    code: str | None = None
    name: str | None = None
    full_name: str | None = None
    address: str | None = None


class DoctorCreateRequest(StrictRequest):
    first_name: str
    last_name: str | None = None
    patronymic: str | None = None


class DoctorUpdateRequest(StrictRequest):
    first_name: str | None = None
    last_name: str | None = None
    patronymic: str | None = None


class SampleTypeCreateRequest(StrictRequest):
    code: str
    name: str


class SampleTypeUpdateRequest(StrictRequest):
    code: str | None = None
    name: str | None = None


class ResearchGoalCreateRequest(StrictRequest):
    code: str
    name: str
    comment: str | None = None
    lab_id: UUID | None = None


class ResearchGoalUpdateRequest(StrictRequest):
    code: str | None = None
    name: str | None = None
    comment: str | None = None
    lab_id: UUID | None = None


class IndicatorCreateRequest(StrictRequest):
    name: str
    unit: str | None = None
    norm_text: str | None = None
    norm_value: str | None = None
    default_text: str | None = None
    comment: str | None = None
    research_goal_id: UUID | None = None
    sample_type_id: UUID | None = None


class IndicatorUpdateRequest(StrictRequest):
    name: str | None = None
    unit: str | None = None
    norm_text: str | None = None
    norm_value: str | None = None
    default_text: str | None = None
    comment: str | None = None
    research_goal_id: UUID | None = None
    sample_type_id: UUID | None = None


class ConclusionCreateRequest(StrictRequest):
    code: str
    name: str
    text_singular: str
    text_plural: str
    comment: str | None = None


class ConclusionUpdateRequest(StrictRequest):
    code: str | None = None
    name: str | None = None
    text_singular: str | None = None
    text_plural: str | None = None
    comment: str | None = None


class ProtocolTypeCreateRequest(StrictRequest):
    code: str | None = None
    name: str


class ProtocolTypeUpdateRequest(StrictRequest):
    code: str | None = None
    name: str | None = None
