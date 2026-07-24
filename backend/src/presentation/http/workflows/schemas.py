from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- Templates ---------------------------------------------------------------


class TemplateCreateRequest(StrictRequest):
    title: str
    current_version: int = 0


class TemplateUpdateRequest(StrictRequest):
    title: str | None = None
    current_version: int | None = None


# --- Runs --------------------------------------------------------------------


class RunCreateRequest(StrictRequest):
    template_id: UUID
    schema_version: int | None = None
    title: str
    scope_kind: str | None = None
    scope_id: UUID | None = None
    answers: dict[str, Any] = Field(default_factory=dict)
    loops: dict[str, Any] = Field(default_factory=dict)
    history: list[Any] = Field(default_factory=list)
    current_node_id: str | None = None
    created_by: UUID | None = None


class RunUpdateRequest(StrictRequest):
    """PATCH accepts only executor-editable fields — never status or events."""

    title: str | None = None
    answers: dict[str, Any] | None = None
    loops: dict[str, Any] | None = None
    history: list[Any] | None = None
    current_node_id: str | None = None


class AddCommentRequest(StrictRequest):
    text: str
    node_id: str | None = None
    author: str | None = None


# --- Execute step ------------------------------------------------------------


class ExecuteStepActionRequest(StrictRequest):
    action_id: str
    command: str
    resolved_args: dict[str, Any] = Field(default_factory=dict)


class ExecuteStepRequest(StrictRequest):
    node_id: str
    attempt: int = Field(ge=0)
    actions: list[ExecuteStepActionRequest] = Field(default_factory=list)
    actor_id: UUID | None = None
    author: str | None = None


# --- Import ------------------------------------------------------------------


class ImportVersionRequest(StrictRequest):
    version: int
    # Aliased so the JSON key stays "schema" without shadowing BaseModel.schema.
    schema_body: dict[str, Any] = Field(alias="schema")


class ImportEventRequest(StrictRequest):
    kind: str
    node_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    author: str | None = None


class ImportRunRequest(StrictRequest):
    schema_version: int
    title: str
    status: str = "draft"
    scope_kind: str | None = None
    scope_id: UUID | None = None
    answers: dict[str, Any] = Field(default_factory=dict)
    loops: dict[str, Any] = Field(default_factory=dict)
    history: list[Any] = Field(default_factory=list)
    current_node_id: str | None = None
    created_by: UUID | None = None
    events: list[ImportEventRequest] = Field(default_factory=list)


class ImportTemplateRequest(StrictRequest):
    title: str
    current_version: int = 0
    versions: list[ImportVersionRequest] = Field(default_factory=list)
    runs: list[ImportRunRequest] = Field(default_factory=list)


class ImportRequest(StrictRequest):
    templates: list[ImportTemplateRequest] = Field(default_factory=list)
