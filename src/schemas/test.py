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


class TestCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str | None = None
    comment: str | None = None
    norm: str | None = None
    is_active: bool
    result_id: UUID
    indicator_id: UUID | None = None
    status_id: UUID | None = None


class TestReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    value: str | None = None
    comment: str | None = None
    norm: str | None = None
    is_active: bool
    result_id: UUID
    indicator_id: UUID | None = None
    status_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    result: EntityRefDTO | None = None
    indicator: EntityRefDTO | None = None
    status: EntityRefDTO | None = None


TestListReadDTO = TestReadDTO


class TestUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str | None = None
    comment: str | None = None
    norm: str | None = None
    is_active: bool | None = None
    result_id: UUID | None = None
    indicator_id: UUID | None = None
    status_id: UUID | None = None


class TestDeleteDTO(DeleteRequestDTO):
    id: UUID


class TestReadEnvelopeDTO(ReadResponseDTO[TestReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class TestListEnvelopeDTO(ListResponseDTO[TestListReadDTO]):
    meta: ListMetaDTO


class TestCreateEnvelopeDTO(ActionResponseDTO[TestReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class TestUpdateEnvelopeDTO(ActionResponseDTO[TestReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class TestDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
