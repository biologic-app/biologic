from typing import Literal

from pydantic import BaseModel, Field

SortOrder = Literal["asc", "desc"]


class PageMeta(BaseModel):
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1)
