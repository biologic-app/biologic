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
    ListMetaDTO,
    ListResponseDTO,
    ReadMetaDTO,
    ReadResponseDTO,
)


class SampleStatusCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str | None = None
    name: str


class SampleStatusReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    code: str | None = None
    name: str
    created_at: datetime
    updated_at: datetime


SampleStatusListReadDTO = SampleStatusReadDTO


class SampleStatusUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str | None = None
    name: str | None = None


class SampleStatusDeleteDTO(DeleteRequestDTO):
    id: UUID


class SampleStatusReadEnvelopeDTO(ReadResponseDTO[SampleStatusReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class SampleStatusListEnvelopeDTO(ListResponseDTO[SampleStatusListReadDTO]):
    meta: ListMetaDTO


class SampleStatusCreateEnvelopeDTO(ActionResponseDTO[SampleStatusReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class SampleStatusUpdateEnvelopeDTO(ActionResponseDTO[SampleStatusReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class SampleStatusDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
