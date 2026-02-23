from __future__ import annotations

from datetime import datetime
from typing import Any
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


class ChangeLogCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    branch_id: UUID | None = None
    entity_type: str | None = None
    entity_id: UUID | None = None
    action: str | None = None
    actor_id: UUID | None = None
    actor_name: str | None = None
    snapshot: dict[str, Any] | None = None
    diff: dict[str, Any] | None = None


class ChangeLogReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    branch_id: UUID | None = None
    entity_type: str | None = None
    entity_id: UUID | None = None
    action: str | None = None
    actor_id: UUID | None = None
    actor_name: str | None = None
    snapshot: dict[str, Any] | None = None
    diff: dict[str, Any] | None = None
    created_at: datetime
    branch: EntityRefDTO | None = None
    entity: EntityRefDTO | None = None
    actor: EntityRefDTO | None = None


ChangeLogListReadDTO = ChangeLogReadDTO


class ChangeLogUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")
    branch_id: UUID | None = None
    entity_type: str | None = None
    entity_id: UUID | None = None
    action: str | None = None
    actor_id: UUID | None = None
    actor_name: str | None = None
    snapshot: dict[str, Any] | None = None
    diff: dict[str, Any] | None = None


class ChangeLogDeleteDTO(DeleteRequestDTO):
    id: UUID


class ChangeLogReadEnvelopeDTO(ReadResponseDTO[ChangeLogReadDTO]):
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class ChangeLogListEnvelopeDTO(ListResponseDTO[ChangeLogListReadDTO]):
    meta: ListMetaDTO


class ChangeLogCreateEnvelopeDTO(ActionResponseDTO[ChangeLogReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class ChangeLogUpdateEnvelopeDTO(ActionResponseDTO[ChangeLogReadDTO]):
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class ChangeLogDeleteEnvelopeDTO(DeleteResponseDTO):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
