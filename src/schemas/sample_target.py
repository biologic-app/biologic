from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.base import (
    ActionMetaDTO,
    ActionResponseDTO,
    DeleteMetaDTO,
    DeleteRequestDTO,
    DeleteResponseDTO,
    EntityRefDTO,
    ListMetaDTO,
    ListResponseDTO,
    ReadMetaDTO,
    ReadResponseDTO,
)


class SampleTargetCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sample_id: UUID
    research_goal_id: UUID
    status_id: UUID | None = None


class SampleTargetReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    sample_id: UUID
    research_goal_id: UUID
    status_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    sample: EntityRefDTO | None = None
    research_goal: EntityRefDTO | None = None
    status: EntityRefDTO | None = None


SampleTargetListReadDTO = SampleTargetReadDTO


class SampleTargetUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sample_id: UUID | None = None
    research_goal_id: UUID | None = None
    status_id: UUID | None = None


class SampleTargetDeleteDTO(DeleteRequestDTO):
    id: UUID


class SampleTargetReadEnvelopeDTO(ReadResponseDTO[SampleTargetReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class SampleTargetListEnvelopeDTO(ListResponseDTO[SampleTargetListReadDTO]):
    meta: ListMetaDTO


class SampleTargetCreateEnvelopeDTO(ActionResponseDTO[SampleTargetReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class SampleTargetUpdateEnvelopeDTO(ActionResponseDTO[SampleTargetReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class SampleTargetDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
