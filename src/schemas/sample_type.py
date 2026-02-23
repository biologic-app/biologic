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


class SampleTypeCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    name: str


class SampleTypeReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    code: str
    name: str
    created_at: datetime
    updated_at: datetime


SampleTypeListReadDTO = SampleTypeReadDTO


class SampleTypeUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str | None = None
    name: str | None = None


class SampleTypeDeleteDTO(DeleteRequestDTO):
    id: UUID


class SampleTypeReadEnvelopeDTO(ReadResponseDTO[SampleTypeReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class SampleTypeListEnvelopeDTO(ListResponseDTO[SampleTypeListReadDTO]):
    meta: ListMetaDTO


class SampleTypeCreateEnvelopeDTO(ActionResponseDTO[SampleTypeReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class SampleTypeUpdateEnvelopeDTO(ActionResponseDTO[SampleTypeReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class SampleTypeDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
