from __future__ import annotations

from datetime import UTC, datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

DataT = TypeVar("DataT")


def utc_now() -> datetime:
    return datetime.now(UTC)


class EntityRefDTO(BaseModel):
    """Universal expanded reference for *_id fields."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    name: str | None = None
    code: str | None = None


class ResponseMetaDTO(BaseModel):
    """Base metadata for any API DTO envelope."""

    model_config = ConfigDict(extra="allow")

    timestamp: datetime = Field(default_factory=utc_now)
    request_id: str | None = None
    version: str = "v1"


class ReadMetaDTO(ResponseMetaDTO):
    includes: list[str] = Field(default_factory=list)
    includes_requested: list[str] = Field(default_factory=list)
    includes_applied: list[str] = Field(default_factory=list)
    includes_allowed: list[str] = Field(default_factory=list)


class ListMetaDTO(ResponseMetaDTO):
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1)
    includes_requested: list[str] = Field(default_factory=list)
    includes_applied: list[str] = Field(default_factory=list)
    includes_allowed: list[str] = Field(default_factory=list)


class ActionMetaDTO(ResponseMetaDTO):
    operation: str | None = None


class DeleteMetaDTO(ResponseMetaDTO):
    operation: str = "soft_delete"
    deleted: bool = True


class ReadResponseDTO(BaseModel, Generic[DataT]):
    data: DataT
    meta: ReadMetaDTO = Field(default_factory=ReadMetaDTO)


class ListResponseDTO(BaseModel, Generic[DataT]):
    items: list[DataT]
    meta: ListMetaDTO


class ActionResponseDTO(BaseModel, Generic[DataT]):
    data: DataT
    meta: ActionMetaDTO = Field(default_factory=ActionMetaDTO)


class DeleteRequestDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = None


class DeleteResponseDTO(BaseModel):
    meta: DeleteMetaDTO = Field(default_factory=DeleteMetaDTO)
