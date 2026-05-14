from typing import Literal

from pydantic import BaseModel, Field, field_validator

SortOrder = Literal["asc", "desc"]


class PaginationParams(BaseModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1)
    sort_by: str | None = None
    sort_order: SortOrder = "asc"
    filters: str | None = None
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


class PageMeta(BaseModel):
    timestamp: str | None = None
    request_id: str | None = None
    version: str = "v1"
    total: int
    offset: int
    limit: int
    next_cursor: str | None = None
    has_more: bool
    includes_requested: list[str] = Field(default_factory=list)
    includes_applied: list[str] = Field(default_factory=list)
    includes_allowed: list[str] = Field(default_factory=list)
