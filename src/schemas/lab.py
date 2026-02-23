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


class LabCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    branch_id: UUID | None = None
    code: str
    name: str
    full_name: str | None = None


class LabReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    branch_id: UUID | None = None
    code: str
    name: str
    full_name: str | None = None
    created_at: datetime
    updated_at: datetime
    branch: EntityRefDTO | None = None


LabListReadDTO = LabReadDTO


class LabUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    branch_id: UUID | None = None
    code: str | None = None
    name: str | None = None
    full_name: str | None = None


class LabDeleteDTO(DeleteRequestDTO):
    id: UUID


class LabReadEnvelopeDTO(ReadResponseDTO[LabReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class LabListEnvelopeDTO(ListResponseDTO[LabListReadDTO]):
    meta: ListMetaDTO


class LabCreateEnvelopeDTO(ActionResponseDTO[LabReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class LabUpdateEnvelopeDTO(ActionResponseDTO[LabReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class LabDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
