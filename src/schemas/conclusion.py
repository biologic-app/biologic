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


class ConclusionCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    comment: str | None = None
    conclusion_status_id: UUID


class ConclusionReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    comment: str | None = None
    conclusion_status_id: UUID
    created_at: datetime
    updated_at: datetime
    conclusion_status: EntityRefDTO | None = None


ConclusionListReadDTO = ConclusionReadDTO


class ConclusionUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    comment: str | None = None
    conclusion_status_id: UUID | None = None


class ConclusionDeleteDTO(DeleteRequestDTO):
    id: UUID


class ConclusionReadEnvelopeDTO(ReadResponseDTO[ConclusionReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class ConclusionListEnvelopeDTO(ListResponseDTO[ConclusionListReadDTO]):
    meta: ListMetaDTO


class ConclusionCreateEnvelopeDTO(ActionResponseDTO[ConclusionReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class ConclusionUpdateEnvelopeDTO(ActionResponseDTO[ConclusionReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class ConclusionDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
