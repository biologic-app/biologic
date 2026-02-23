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


class IndicatorCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    unit: str | None = None
    norm_text: str | None = None
    norm_value: str | None = None
    default_text: str | None = None
    comment: str | None = None
    lab_id: UUID | None = None
    sample_type_id: UUID | None = None


class IndicatorReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    name: str
    unit: str | None = None
    norm_text: str | None = None
    norm_value: str | None = None
    default_text: str | None = None
    comment: str | None = None
    lab_id: UUID | None = None
    sample_type_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    lab: EntityRefDTO | None = None
    sample_type: EntityRefDTO | None = None


IndicatorListReadDTO = IndicatorReadDTO


class IndicatorUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    unit: str | None = None
    norm_text: str | None = None
    norm_value: str | None = None
    default_text: str | None = None
    comment: str | None = None
    lab_id: UUID | None = None
    sample_type_id: UUID | None = None


class IndicatorDeleteDTO(DeleteRequestDTO):
    id: UUID


class IndicatorReadEnvelopeDTO(ReadResponseDTO[IndicatorReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class IndicatorListEnvelopeDTO(ListResponseDTO[IndicatorListReadDTO]):
    meta: ListMetaDTO


class IndicatorCreateEnvelopeDTO(ActionResponseDTO[IndicatorReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class IndicatorUpdateEnvelopeDTO(ActionResponseDTO[IndicatorReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class IndicatorDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
