from __future__ import annotations

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
    permission_id: UUID


class RolePermissionReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    role_id: UUID
    permission_id: UUID
    role: EntityRefDTO | None = None
    permission: EntityRefDTO | None = None


RolePermissionListReadDTO = RolePermissionReadDTO


class RolePermissionUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role_id: UUID | None = None
    permission_id: UUID | None = None


class RolePermissionDeleteDTO(DeleteRequestDTO):
    id: UUID


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
