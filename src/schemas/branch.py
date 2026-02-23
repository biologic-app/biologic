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


class BranchCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str | None = None
    name: str | None = None


class BranchReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    code: str | None = None
    name: str | None = None
    created_at: datetime
    updated_at: datetime


BranchListReadDTO = BranchReadDTO


class BranchUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str | None = None
    name: str | None = None


class BranchDeleteDTO(DeleteRequestDTO):
    id: UUID


class BranchReadEnvelopeDTO(ReadResponseDTO[BranchReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class BranchListEnvelopeDTO(ListResponseDTO[BranchListReadDTO]):
    meta: ListMetaDTO


class BranchCreateEnvelopeDTO(ActionResponseDTO[BranchReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class BranchUpdateEnvelopeDTO(ActionResponseDTO[BranchReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class BranchDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
