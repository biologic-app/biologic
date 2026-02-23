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


class ConclusionStatusCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str | None = None
    name: str | None = None


class ConclusionStatusReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    code: str | None = None
    name: str | None = None
    created_at: datetime
    updated_at: datetime


ConclusionStatusListReadDTO = ConclusionStatusReadDTO


class ConclusionStatusUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str | None = None
    name: str | None = None


class ConclusionStatusDeleteDTO(DeleteRequestDTO):
    id: UUID


class ConclusionStatusReadEnvelopeDTO(ReadResponseDTO[ConclusionStatusReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class ConclusionStatusListEnvelopeDTO(ListResponseDTO[ConclusionStatusListReadDTO]):
    meta: ListMetaDTO


class ConclusionStatusCreateEnvelopeDTO(ActionResponseDTO[ConclusionStatusReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class ConclusionStatusUpdateEnvelopeDTO(ActionResponseDTO[ConclusionStatusReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class ConclusionStatusDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
