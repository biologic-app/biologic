from __future__ import annotations

from datetime import datetime
from typing import Literal
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


class RoleCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str
    name: str
    scope_type: Literal["global", "own_branch", "own_lab", "own_objects"]


class RoleReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    key: str
    name: str
    scope_type: Literal["global", "own_branch", "own_lab", "own_objects"]
    created_at: datetime
    updated_at: datetime


RoleListReadDTO = RoleReadDTO


class RoleUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str | None = None
    name: str | None = None
    scope_type: Literal["global", "own_branch", "own_lab", "own_objects"] | None = None


class RoleDeleteDTO(DeleteRequestDTO):
    id: UUID


class RoleReadEnvelopeDTO(ReadResponseDTO[RoleReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class RoleListEnvelopeDTO(ListResponseDTO[RoleListReadDTO]):
    meta: ListMetaDTO


class RoleCreateEnvelopeDTO(ActionResponseDTO[RoleReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class RoleUpdateEnvelopeDTO(ActionResponseDTO[RoleReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class RoleDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
