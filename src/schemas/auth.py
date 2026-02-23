from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.base import ActionMetaDTO, ActionResponseDTO


class AuthLoginDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str
    password: str


class AuthUserDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    username: str
    role_id: UUID
    role_key: str
    role_name: str
    first_name: str | None = None
    last_name: str | None = None
    patronymic: str | None = None


class AuthPermissionDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resource: str
    action: str


class AuthSessionDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user: AuthUserDTO
    permissions: list[AuthPermissionDTO] = Field(default_factory=list)
    access_expires_at: datetime
    refresh_expires_at: datetime | None = None


class AuthSessionEnvelopeDTO(ActionResponseDTO[AuthSessionDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class AuthLogoutEnvelopeDTO(BaseModel):
    meta: ActionMetaDTO = Field(default_factory=lambda: ActionMetaDTO(operation="logout"))
