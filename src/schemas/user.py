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


class UserCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str
    password_hash: str
    code: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    patronymic: str | None = None
    is_registrar: bool | None = None
    is_lab_head: bool | None = None
    is_branch_head: bool | None = None
    role_id: UUID
    lab_id: UUID | None = None


class UserReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    username: str
    code: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    patronymic: str | None = None
    is_registrar: bool | None = None
    is_lab_head: bool | None = None
    is_branch_head: bool | None = None
    role_id: UUID
    lab_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    role: EntityRefDTO | None = None
    lab: EntityRefDTO | None = None


UserListReadDTO = UserReadDTO


class UserUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str | None = None
    password_hash: str | None = None
    code: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    patronymic: str | None = None
    is_registrar: bool | None = None
    is_lab_head: bool | None = None
    is_branch_head: bool | None = None
    role_id: UUID | None = None
    lab_id: UUID | None = None


class UserDeleteDTO(DeleteRequestDTO):
    id: UUID


class UserReadEnvelopeDTO(ReadResponseDTO[UserReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class UserListEnvelopeDTO(ListResponseDTO[UserListReadDTO]):
    meta: ListMetaDTO


class UserCreateEnvelopeDTO(ActionResponseDTO[UserReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class UserUpdateEnvelopeDTO(ActionResponseDTO[UserReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class UserDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
