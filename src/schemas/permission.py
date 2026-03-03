from __future__ import annotations

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


class PermissionCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resource: str
    action: str


class PermissionReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    resource: str
    action: str


PermissionListReadDTO = PermissionReadDTO


class PermissionUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resource: str | None = None
    action: str | None = None


class PermissionDeleteDTO(DeleteRequestDTO):
    id: UUID


class PermissionReadEnvelopeDTO(ReadResponseDTO[PermissionReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class PermissionListEnvelopeDTO(ListResponseDTO[PermissionListReadDTO]):
    meta: ListMetaDTO


class PermissionCreateEnvelopeDTO(ActionResponseDTO[PermissionReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class PermissionUpdateEnvelopeDTO(ActionResponseDTO[PermissionReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class PermissionDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
