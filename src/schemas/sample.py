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


class SampleCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    month_no: int | None = None
    name: str
    alternate_name: str | None = None
    mass: str | None = None
    target_description: str | None = None
    comment: str | None = None
    section: str | None = None
    delivery: str | None = None
    nomenclature_code: str | None = None
    batch_code: str | None = None
    supplier: str | None = None
    is_urgent: bool
    is_done: bool
    sample_type_id: UUID | None = None
    status_id: UUID | None = None
    direction_id: UUID | None = None
    protocol_id: UUID | None = None
    sampled_at: datetime | None = None
    received_at: datetime | None = None
    completed_at: datetime | None = None


class SampleReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    month_no: int | None = None
    name: str
    alternate_name: str | None = None
    mass: str | None = None
    target_description: str | None = None
    comment: str | None = None
    section: str | None = None
    delivery: str | None = None
    nomenclature_code: str | None = None
    batch_code: str | None = None
    supplier: str | None = None
    is_urgent: bool
    is_done: bool
    sample_type_id: UUID | None = None
    status_id: UUID | None = None
    direction_id: UUID | None = None
    protocol_id: UUID | None = None
    sampled_at: datetime | None = None
    received_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    sample_type: EntityRefDTO | None = None
    status: EntityRefDTO | None = None
    direction: EntityRefDTO | None = None
    protocol: EntityRefDTO | None = None


SampleListReadDTO = SampleReadDTO


class SampleUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    month_no: int | None = None
    name: str | None = None
    alternate_name: str | None = None
    mass: str | None = None
    target_description: str | None = None
    comment: str | None = None
    section: str | None = None
    delivery: str | None = None
    nomenclature_code: str | None = None
    batch_code: str | None = None
    supplier: str | None = None
    is_urgent: bool | None = None
    is_done: bool | None = None
    sample_type_id: UUID | None = None
    status_id: UUID | None = None
    direction_id: UUID | None = None
    protocol_id: UUID | None = None
    sampled_at: datetime | None = None
    received_at: datetime | None = None
    completed_at: datetime | None = None


class SampleDeleteDTO(DeleteRequestDTO):
    id: UUID


class SampleReadEnvelopeDTO(ReadResponseDTO[SampleReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class SampleListEnvelopeDTO(ListResponseDTO[SampleListReadDTO]):
    meta: ListMetaDTO


class SampleCreateEnvelopeDTO(ActionResponseDTO[SampleReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class SampleUpdateEnvelopeDTO(ActionResponseDTO[SampleReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class SampleDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
