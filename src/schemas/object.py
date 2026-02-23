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


class ObjectCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    branch_id: UUID | None = None
    code: str
    name: str
    full_name: str | None = None
    address: str | None = None


class ObjectReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    branch_id: UUID | None = None
    code: str
    name: str
    full_name: str | None = None
    address: str | None = None
    created_at: datetime
    updated_at: datetime
    branch: EntityRefDTO | None = None


ObjectListReadDTO = ObjectReadDTO


class ObjectUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    branch_id: UUID | None = None
    code: str | None = None
    name: str | None = None
    full_name: str | None = None
    address: str | None = None


class ObjectDeleteDTO(DeleteRequestDTO):
    id: UUID


class ObjectReadEnvelopeDTO(ReadResponseDTO[ObjectReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class ObjectListEnvelopeDTO(ListResponseDTO[ObjectListReadDTO]):
    meta: ListMetaDTO


class ObjectCreateEnvelopeDTO(ActionResponseDTO[ObjectReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class ObjectUpdateEnvelopeDTO(ActionResponseDTO[ObjectReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class ObjectDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
