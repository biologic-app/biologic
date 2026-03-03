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


class ResearchCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sample_id: UUID
    research_goal_id: UUID
    status_id: UUID | None = None
    comment: str | None = None
    recommendation: str | None = None
    received_at: datetime | None = None
    completed_at: datetime | None = None


class ResearchReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    sample_id: UUID
    research_goal_id: UUID
    status_id: UUID | None = None
    comment: str | None = None
    recommendation: str | None = None
    received_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    sample: EntityRefDTO | None = None
    research_goal: EntityRefDTO | None = None
    status: EntityRefDTO | None = None


ResearchListReadDTO = ResearchReadDTO


class ResearchUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sample_id: UUID | None = None
    research_goal_id: UUID | None = None
    status_id: UUID | None = None
    comment: str | None = None
    recommendation: str | None = None
    received_at: datetime | None = None
    completed_at: datetime | None = None


class ResearchDeleteDTO(DeleteRequestDTO):
    id: UUID


class ResearchReadEnvelopeDTO(ReadResponseDTO[ResearchReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class ResearchListEnvelopeDTO(ListResponseDTO[ResearchListReadDTO]):
    meta: ListMetaDTO


class ResearchCreateEnvelopeDTO(ActionResponseDTO[ResearchReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class ResearchUpdateEnvelopeDTO(ActionResponseDTO[ResearchReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class ResearchDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
