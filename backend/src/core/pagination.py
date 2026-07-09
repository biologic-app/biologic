from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from src.core.errors import BadRequestError

SortOrder = Literal["asc", "desc"]


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class PaginationParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=50, ge=1)
    cursor: str | None = None
    sort_by: str | None = None
    sort_order: SortOrder = "asc"
    filters: str | None = None
    search: str | None = None
    include: str | None = None

    @field_validator("limit")
    @classmethod
    def cap_limit(cls, value: int) -> int:
        return min(value, 100)

    @property
    def includes_requested(self) -> list[str]:
        if not self.include:
            return []
        return [item.strip() for item in self.include.split(",") if item.strip()]


def get_pagination_params(
    request: Request,
    limit: int = Query(default=50, ge=1),
    cursor: str | None = None,
    sort_by: str | None = None,
    sort_order: SortOrder = "asc",
    filters: str | None = None,
    search: str | None = None,
    include: str | None = None,
) -> PaginationParams:
    if "offset" in request.query_params:
        raise BadRequestError("Offset pagination is not supported. Use cursor pagination.")
    return PaginationParams(
        limit=limit,
        cursor=cursor,
        sort_by=sort_by,
        sort_order=sort_order,
        filters=filters,
        search=search,
        include=include,
    )


PaginationDependency = Annotated[PaginationParams, Depends(get_pagination_params)]


class PageMeta(BaseModel):
    timestamp: str = Field(default_factory=utc_now_iso)
    request_id: UUID | None = None
    version: str = "v1"
    total: int
    limit: int
    next_cursor: str | None = None
    has_more: bool
    includes_requested: list[str] = Field(default_factory=list)
    includes_applied: list[str] = Field(default_factory=list)
    includes_allowed: list[str] = Field(default_factory=list)

    @field_serializer("request_id")
    def serialize_request_id(self, value: UUID | None) -> str | None:
        return str(value) if value else None
