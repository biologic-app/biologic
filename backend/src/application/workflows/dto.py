from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class StepActionInput:
    action_id: str
    command: str
    resolved_args: dict[str, Any]


@dataclass(frozen=True)
class ExecuteStepInput:
    run_id: UUID
    node_id: str
    attempt: int
    actions: list[StepActionInput]
    actor_id: UUID | None = None
    author: str | None = None


@dataclass(frozen=True)
class ExecuteStepResult:
    status: str  # "applied" | "already_applied"
    already_applied: bool
    node_id: str
    attempt: int
    results: list[dict[str, Any]]


# --- Bulk import (localStorage → backend) -------------------------------------


@dataclass(frozen=True)
class ImportVersionInput:
    version: int
    schema: dict[str, Any]


@dataclass(frozen=True)
class ImportEventInput:
    kind: str
    node_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    author: str | None = None


@dataclass(frozen=True)
class ImportRunInput:
    schema_version: int
    title: str
    status: str = "draft"
    scope_kind: str | None = None
    scope_id: UUID | None = None
    answers: dict[str, Any] = field(default_factory=dict)
    loops: dict[str, Any] = field(default_factory=dict)
    history: list[Any] = field(default_factory=list)
    current_node_id: str | None = None
    created_by: UUID | None = None
    events: list[ImportEventInput] = field(default_factory=list)


@dataclass(frozen=True)
class ImportTemplateInput:
    title: str
    current_version: int = 0
    versions: list[ImportVersionInput] = field(default_factory=list)
    runs: list[ImportRunInput] = field(default_factory=list)


@dataclass(frozen=True)
class ImportResult:
    templates: int
    versions: int
    runs: int
    events: int
