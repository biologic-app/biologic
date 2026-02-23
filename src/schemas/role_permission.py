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


class RolePermissionCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role_id: UUID
    resource: str
    action: str


class RolePermissionReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    role_id: UUID
    resource: str
    action: str
    created_at: datetime
    updated_at: datetime
    role: EntityRefDTO | None = None


RolePermissionListReadDTO = RolePermissionReadDTO


class RolePermissionUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role_id: UUID | None = None
    resource: str | None = None
    action: str | None = None


class RolePermissionDeleteDTO(DeleteRequestDTO):
    role_id: UUID
    resource: str
    action: str


class RolePermissionReadEnvelopeDTO(ReadResponseDTO[RolePermissionReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class RolePermissionListEnvelopeDTO(ListResponseDTO[RolePermissionListReadDTO]):
    meta: ListMetaDTO


class RolePermissionCreateEnvelopeDTO(ActionResponseDTO[RolePermissionReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class RolePermissionUpdateEnvelopeDTO(ActionResponseDTO[RolePermissionReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class RolePermissionDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
