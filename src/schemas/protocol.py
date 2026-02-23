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


class ProtocolCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    year_no: int
    copies: int | None = None
    is_signed: bool
    protocol_copy_name: str | None = None
    excerpt_copy_name: str | None = None
    conclusion_id: UUID | None = None
    protocol_type_id: UUID | None = None
    issued_at: datetime | None = None


class ProtocolReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    year_no: int
    copies: int | None = None
    is_signed: bool
    protocol_copy_name: str | None = None
    excerpt_copy_name: str | None = None
    conclusion_id: UUID | None = None
    protocol_type_id: UUID | None = None
    issued_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    conclusion: EntityRefDTO | None = None
    protocol_type: EntityRefDTO | None = None


ProtocolListReadDTO = ProtocolReadDTO


class ProtocolUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    year_no: int | None = None
    copies: int | None = None
    is_signed: bool | None = None
    protocol_copy_name: str | None = None
    excerpt_copy_name: str | None = None
    conclusion_id: UUID | None = None
    protocol_type_id: UUID | None = None
    issued_at: datetime | None = None


class ProtocolDeleteDTO(DeleteRequestDTO):
    id: UUID


class ProtocolReadEnvelopeDTO(ReadResponseDTO[ProtocolReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class ProtocolListEnvelopeDTO(ListResponseDTO[ProtocolListReadDTO]):
    meta: ListMetaDTO


class ProtocolCreateEnvelopeDTO(ActionResponseDTO[ProtocolReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class ProtocolUpdateEnvelopeDTO(ActionResponseDTO[ProtocolReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class ProtocolDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
