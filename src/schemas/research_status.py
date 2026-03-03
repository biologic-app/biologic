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


class ResearchStatusCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str | None = None
    name: str


class ResearchStatusReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    code: str | None = None
    name: str
    created_at: datetime
    updated_at: datetime


ResearchStatusListReadDTO = ResearchStatusReadDTO


class ResearchStatusUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str | None = None
    name: str | None = None


class ResearchStatusDeleteDTO(DeleteRequestDTO):
    id: UUID


class ResearchStatusReadEnvelopeDTO(ReadResponseDTO[ResearchStatusReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class ResearchStatusListEnvelopeDTO(ListResponseDTO[ResearchStatusListReadDTO]):
    meta: ListMetaDTO


class ResearchStatusCreateEnvelopeDTO(ActionResponseDTO[ResearchStatusReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class ResearchStatusUpdateEnvelopeDTO(ActionResponseDTO[ResearchStatusReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class ResearchStatusDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
