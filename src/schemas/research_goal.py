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


class ResearchGoalCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    name: str
    comment: str | None = None
    lab_id: UUID | None = None


class ResearchGoalReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    code: str
    name: str
    comment: str | None = None
    lab_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    lab: EntityRefDTO | None = None


ResearchGoalListReadDTO = ResearchGoalReadDTO


class ResearchGoalUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str | None = None
    name: str | None = None
    comment: str | None = None
    lab_id: UUID | None = None


class ResearchGoalDeleteDTO(DeleteRequestDTO):
    id: UUID


class ResearchGoalReadEnvelopeDTO(ReadResponseDTO[ResearchGoalReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class ResearchGoalListEnvelopeDTO(ListResponseDTO[ResearchGoalListReadDTO]):
    meta: ListMetaDTO


class ResearchGoalCreateEnvelopeDTO(ActionResponseDTO[ResearchGoalReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class ResearchGoalUpdateEnvelopeDTO(ActionResponseDTO[ResearchGoalReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class ResearchGoalDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
