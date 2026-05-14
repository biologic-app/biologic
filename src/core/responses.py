from datetime import UTC, datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer

from src.core.pagination import PageMeta

T = TypeVar("T")


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class ResponseMeta(BaseModel):
    timestamp: str = Field(default_factory=utc_now_iso)
    request_id: UUID | None = None
    version: str = "v1"
    includes: list[str] = Field(default_factory=list)
    includes_requested: list[str] = Field(default_factory=list)
    includes_applied: list[str] = Field(default_factory=list)
    includes_allowed: list[str] = Field(default_factory=list)
    operation: str | None = None

    @field_serializer("request_id")
    def serialize_request_id(self, value: UUID | None) -> str | None:
        return str(value) if value else None


class SingleResponse(BaseModel, Generic[T]):
    data: T
    meta: ResponseMeta


class ListResponse(BaseModel, Generic[T]):
    items: list[T]
    meta: PageMeta
