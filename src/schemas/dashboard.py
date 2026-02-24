from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.base import ActionMetaDTO, ActionResponseDTO, ListResponseDTO


class DashboardQuickActionDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    label: str
    resource: str
    action: str
    to: str
    icon: str
    createdAt: datetime
    updatedAt: datetime


class DashboardQuickActionCreateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=120)
    resource: str = Field(min_length=1, max_length=64)
    action: str = Field(min_length=1, max_length=32)
    to: str = Field(min_length=1, max_length=255)
    icon: str = Field(min_length=1, max_length=120)


class DashboardQuickActionUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str | None = Field(default=None, min_length=1, max_length=120)
    resource: str | None = Field(default=None, min_length=1, max_length=64)
    action: str | None = Field(default=None, min_length=1, max_length=32)
    to: str | None = Field(default=None, min_length=1, max_length=255)
    icon: str | None = Field(default=None, min_length=1, max_length=120)


class DashboardQuickActionListEnvelopeDTO(ListResponseDTO[DashboardQuickActionDTO]):
    pass


class DashboardQuickActionCreateEnvelopeDTO(ActionResponseDTO[DashboardQuickActionDTO]):
    meta: ActionMetaDTO = Field(default_factory=lambda: ActionMetaDTO(operation="create"))


class DashboardQuickActionUpdateEnvelopeDTO(ActionResponseDTO[DashboardQuickActionDTO]):
    meta: ActionMetaDTO = Field(default_factory=lambda: ActionMetaDTO(operation="update"))


class DashboardQuickActionDeleteEnvelopeDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool = True
