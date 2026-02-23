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


class DoctorCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_name: str
    last_name: str | None = None
    patronymic: str | None = None


class DoctorReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    first_name: str
    last_name: str | None = None
    patronymic: str | None = None
    created_at: datetime
    updated_at: datetime


DoctorListReadDTO = DoctorReadDTO


class DoctorUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_name: str | None = None
    last_name: str | None = None
    patronymic: str | None = None


class DoctorDeleteDTO(DeleteRequestDTO):
    id: UUID


class DoctorReadEnvelopeDTO(ReadResponseDTO[DoctorReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class DoctorListEnvelopeDTO(ListResponseDTO[DoctorListReadDTO]):
    meta: ListMetaDTO


class DoctorCreateEnvelopeDTO(ActionResponseDTO[DoctorReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class DoctorUpdateEnvelopeDTO(ActionResponseDTO[DoctorReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class DoctorDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
