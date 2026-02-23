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


class ResultCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    comment: str | None = None
    recommendation: str | None = None
    is_done: bool
    lab_id: UUID | None = None
    sample_id: UUID
    status_id: UUID | None = None
    received_at: datetime | None = None
    completed_at: datetime | None = None


class ResultReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    comment: str | None = None
    recommendation: str | None = None
    is_done: bool
    lab_id: UUID | None = None
    sample_id: UUID
    status_id: UUID | None = None
    received_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    lab: EntityRefDTO | None = None
    sample: EntityRefDTO | None = None
    status: EntityRefDTO | None = None


ResultListReadDTO = ResultReadDTO


class ResultUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    comment: str | None = None
    recommendation: str | None = None
    is_done: bool | None = None
    lab_id: UUID | None = None
    sample_id: UUID | None = None
    status_id: UUID | None = None
    received_at: datetime | None = None
    completed_at: datetime | None = None


class ResultDeleteDTO(DeleteRequestDTO):
    id: UUID


class ResultReadEnvelopeDTO(ReadResponseDTO[ResultReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class ResultListEnvelopeDTO(ListResponseDTO[ResultListReadDTO]):
    meta: ListMetaDTO


class ResultCreateEnvelopeDTO(ActionResponseDTO[ResultReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class ResultUpdateEnvelopeDTO(ActionResponseDTO[ResultReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class ResultDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
