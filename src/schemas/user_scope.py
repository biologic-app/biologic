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


class UserScopeCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: UUID
    scope_id: UUID | None = None


class UserScopeReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    user_id: UUID
    scope_id: UUID | None = None
    user: EntityRefDTO | None = None


UserScopeListReadDTO = UserScopeReadDTO


class UserScopeUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: UUID | None = None
    scope_id: UUID | None = None


class UserScopeDeleteDTO(DeleteRequestDTO):
    id: UUID


class UserScopeReadEnvelopeDTO(ReadResponseDTO[UserScopeReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class UserScopeListEnvelopeDTO(ListResponseDTO[UserScopeListReadDTO]):
    meta: ListMetaDTO


class UserScopeCreateEnvelopeDTO(ActionResponseDTO[UserScopeReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class UserScopeUpdateEnvelopeDTO(ActionResponseDTO[UserScopeReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class UserScopeDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
