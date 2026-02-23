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


class DirectionCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    year_no: int
    base_no: int | None = None
    is_done: bool
    is_urgent: bool
    doctor_id: UUID | None = None
    object_id: UUID | None = None
    status_id: UUID | None = None
    sampled_at: datetime | None = None
    received_at: datetime | None = None
    completed_at: datetime | None = None


class DirectionReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    year_no: int
    base_no: int | None = None
    is_done: bool
    is_urgent: bool
    doctor_id: UUID | None = None
    object_id: UUID | None = None
    status_id: UUID | None = None
    sampled_at: datetime | None = None
    received_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    doctor: EntityRefDTO | None = None
    object: EntityRefDTO | None = None
    status: EntityRefDTO | None = None


DirectionListReadDTO = DirectionReadDTO


class DirectionUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    year_no: int | None = None
    base_no: int | None = None
    is_done: bool | None = None
    is_urgent: bool | None = None
    doctor_id: UUID | None = None
    object_id: UUID | None = None
    status_id: UUID | None = None
    sampled_at: datetime | None = None
    received_at: datetime | None = None
    completed_at: datetime | None = None


class DirectionDeleteDTO(DeleteRequestDTO):
    id: UUID


class DirectionReadEnvelopeDTO(ReadResponseDTO[DirectionReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class DirectionListEnvelopeDTO(ListResponseDTO[DirectionListReadDTO]):
    meta: ListMetaDTO


class DirectionCreateEnvelopeDTO(ActionResponseDTO[DirectionReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class DirectionUpdateEnvelopeDTO(ActionResponseDTO[DirectionReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class DirectionDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
