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


class DirectionStatusCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str | None = None
    name: str


class DirectionStatusReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    code: str | None = None
    name: str
    created_at: datetime
    updated_at: datetime


DirectionStatusListReadDTO = DirectionStatusReadDTO


class DirectionStatusUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str | None = None
    name: str | None = None


class DirectionStatusDeleteDTO(DeleteRequestDTO):
    id: UUID


class DirectionStatusReadEnvelopeDTO(ReadResponseDTO[DirectionStatusReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class DirectionStatusListEnvelopeDTO(ListResponseDTO[DirectionStatusListReadDTO]):
    meta: ListMetaDTO


class DirectionStatusCreateEnvelopeDTO(ActionResponseDTO[DirectionStatusReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class DirectionStatusUpdateEnvelopeDTO(ActionResponseDTO[DirectionStatusReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class DirectionStatusDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
