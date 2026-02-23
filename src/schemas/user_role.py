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


class UserRoleCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: UUID
    role_id: UUID


class UserRoleReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    user_id: UUID
    role_id: UUID
    created_at: datetime
    updated_at: datetime
    user: EntityRefDTO | None = None
    role: EntityRefDTO | None = None


UserRoleListReadDTO = UserRoleReadDTO


class UserRoleUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: UUID | None = None
    role_id: UUID | None = None


class UserRoleDeleteDTO(DeleteRequestDTO):
    id: UUID


class UserRoleReadEnvelopeDTO(ReadResponseDTO[UserRoleReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class UserRoleListEnvelopeDTO(ListResponseDTO[UserRoleListReadDTO]):
    meta: ListMetaDTO


class UserRoleCreateEnvelopeDTO(ActionResponseDTO[UserRoleReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class UserRoleUpdateEnvelopeDTO(ActionResponseDTO[UserRoleReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class UserRoleDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
