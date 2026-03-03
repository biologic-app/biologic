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


class TestStatusCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str | None = None
    name: str


class TestStatusReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    code: str | None = None
    name: str
    created_at: datetime
    updated_at: datetime


TestStatusListReadDTO = TestStatusReadDTO


class TestStatusUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str | None = None
    name: str | None = None


class TestStatusDeleteDTO(DeleteRequestDTO):
    id: UUID


class TestStatusReadEnvelopeDTO(ReadResponseDTO[TestStatusReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class TestStatusListEnvelopeDTO(ListResponseDTO[TestStatusListReadDTO]):
    meta: ListMetaDTO


class TestStatusCreateEnvelopeDTO(ActionResponseDTO[TestStatusReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class TestStatusUpdateEnvelopeDTO(ActionResponseDTO[TestStatusReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class TestStatusDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
