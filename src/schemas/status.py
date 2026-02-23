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


class StatusCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str | None = None
    name: str


class StatusReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    code: str | None = None
    name: str
    created_at: datetime
    updated_at: datetime


StatusListReadDTO = StatusReadDTO


class StatusUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str | None = None
    name: str | None = None


class StatusDeleteDTO(DeleteRequestDTO):
    id: UUID


class StatusReadEnvelopeDTO(ReadResponseDTO[StatusReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class StatusListEnvelopeDTO(ListResponseDTO[StatusListReadDTO]):
    meta: ListMetaDTO


class StatusCreateEnvelopeDTO(ActionResponseDTO[StatusReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class StatusUpdateEnvelopeDTO(ActionResponseDTO[StatusReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class StatusDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
