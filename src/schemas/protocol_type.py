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


class ProtocolTypeCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str | None = None
    name: str


class ProtocolTypeReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    code: str | None = None
    name: str
    created_at: datetime
    updated_at: datetime


ProtocolTypeListReadDTO = ProtocolTypeReadDTO


class ProtocolTypeUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str | None = None
    name: str | None = None


class ProtocolTypeDeleteDTO(DeleteRequestDTO):
    id: UUID


class ProtocolTypeReadEnvelopeDTO(ReadResponseDTO[ProtocolTypeReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class ProtocolTypeListEnvelopeDTO(ListResponseDTO[ProtocolTypeListReadDTO]):
    meta: ListMetaDTO


class ProtocolTypeCreateEnvelopeDTO(ActionResponseDTO[ProtocolTypeReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class ProtocolTypeUpdateEnvelopeDTO(ActionResponseDTO[ProtocolTypeReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class ProtocolTypeDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
