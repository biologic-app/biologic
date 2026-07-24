"""Test doubles for the workflows module (imported by bare name under pytest's
prepend import mode, mirroring tests/contexts/.../application/fakes.py)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace, TracebackType
from typing import Any
from uuid import UUID, uuid4

from src.contexts.laboratory_workflow.application.dto import CommandResult
from src.core.errors import NotFoundError

_MISSING = object()


class FakeLabRepo:
    """Stands in for uow.workflow (laboratory_workflow command methods)."""

    def __init__(self, *, result: CommandResult | None = None) -> None:
        self.result = result or CommandResult(
            id=uuid4(),
            status_id=uuid4(),
            updated_at=datetime(2026, 7, 22, 10, 0, tzinfo=UTC),
        )
        self.complete_calls: list[dict[str, Any]] = []
        self.reject_calls: list[dict[str, Any]] = []
        self.fail_on_complete_call: int | None = None
        self.failure: Exception = RuntimeError("boom")

    async def complete_test(
        self,
        test_id: UUID,
        actor_id: UUID,
        value: str,
        norm: str | None,
        comment: str | None,
        verdict: bool | None,
        workflow_run_id: UUID | None = None,
    ) -> CommandResult:
        self.complete_calls.append(
            {
                "test_id": test_id,
                "actor_id": actor_id,
                "value": value,
                "verdict": verdict,
                "workflow_run_id": workflow_run_id,
            }
        )
        if self.fail_on_complete_call == len(self.complete_calls):
            raise self.failure
        return self.result

    async def reject_test(
        self,
        test_id: UUID,
        actor_id: UUID,
        reason: str,
        workflow_run_id: UUID | None = None,
    ) -> CommandResult:
        self.reject_calls.append(
            {"test_id": test_id, "actor_id": actor_id, "workflow_run_id": workflow_run_id}
        )
        return self.result


class FakeWorkflowsRepo:
    """Stands in for uow.workflows."""

    def __init__(
        self,
        *,
        run: Any = _MISSING,
        status_by_resource: dict[str, str | None] | None = None,
    ) -> None:
        self.run = SimpleNamespace(id=uuid4(), current_version=0) if run is _MISSING else run
        self.status_by_resource = status_by_resource or {}
        self.recorded_steps: list[Any] = []
        self.events: list[Any] = []
        self.created_templates: list[Any] = []
        self.created_versions: list[Any] = []
        self.created_runs: list[Any] = []
        self.attachments: list[Any] = []

    async def get_run(self, run_id: UUID) -> Any:
        if self.run is None:
            raise NotFoundError(f"Workflow run {run_id} was not found.")
        return self.run

    async def find_step_execution(self, run_id: UUID, node_id: str, attempt: int) -> Any:
        for row in self.recorded_steps:
            if row.run_id == run_id and row.node_id == node_id and row.attempt == attempt:
                return row
        return None

    async def read_status_code(self, resource: str, entity_id: UUID) -> str | None:
        return self.status_by_resource.get(resource)

    async def record_step_execution(
        self,
        run_id: UUID,
        node_id: str,
        attempt: int,
        status: str,
        result: dict[str, Any],
    ) -> Any:
        row = SimpleNamespace(
            id=uuid4(),
            run_id=run_id,
            node_id=node_id,
            attempt=attempt,
            status=status,
            result=result,
        )
        self.recorded_steps.append(row)
        return row

    async def append_event(
        self,
        run_id: UUID,
        kind: str,
        node_id: str | None,
        payload: dict[str, Any],
        author: str | None,
    ) -> Any:
        row = SimpleNamespace(
            id=uuid4(),
            run_id=run_id,
            kind=kind,
            node_id=node_id,
            payload=payload,
            author=author,
            created_at=datetime.now(UTC),
        )
        self.events.append(row)
        return row

    # --- import / crud helpers ------------------------------------------
    async def get_template(self, template_id: UUID) -> Any:
        return SimpleNamespace(id=template_id, current_version=0)

    async def create_template(self, values: dict[str, Any]) -> Any:
        row = SimpleNamespace(
            id=uuid4(),
            title=values["title"],
            current_version=values.get("current_version", 0),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.created_templates.append(row)
        return row

    async def update_template(self, template_id: UUID, values: dict[str, Any]) -> Any:
        return SimpleNamespace(id=template_id, **values)

    async def next_version_number(self, template_id: UUID) -> int:
        return len([v for v in self.created_versions if v.template_id == template_id]) + 1

    async def create_version(self, template_id: UUID, version: int, schema: dict[str, Any]) -> Any:
        row = SimpleNamespace(
            id=uuid4(),
            template_id=template_id,
            version=version,
            schema=schema,
            created_at=datetime.now(UTC),
        )
        self.created_versions.append(row)
        return row

    async def create_run(self, values: dict[str, Any]) -> Any:
        row = SimpleNamespace(id=uuid4(), **values)
        self.created_runs.append(row)
        return row

    async def create_attachment(
        self,
        run_id: UUID,
        field_id: str,
        filename: str,
        content_type: str | None,
        size_bytes: int,
        data: bytes,
    ) -> Any:
        row = SimpleNamespace(
            id=uuid4(),
            run_id=run_id,
            field_id=field_id,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            storage="db",
            data=data,
            created_at=datetime.now(UTC),
        )
        self.attachments.append(row)
        return row


class FakeWorkflowsUoW:
    def __init__(self, workflows: FakeWorkflowsRepo, workflow: FakeLabRepo | None = None) -> None:
        self.workflows = workflows
        self.workflow = workflow or FakeLabRepo()
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> FakeWorkflowsUoW:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            self.rolled_back = True

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


def uow_factory(uow: FakeWorkflowsUoW) -> Any:
    return lambda: uow


class RecordingSession:
    """Minimal AsyncSession double: records added rows, no-ops flush/refresh."""

    def __init__(self) -> None:
        self.added: list[Any] = []

    def add(self, instance: Any) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        return None

    async def refresh(self, instance: Any) -> None:
        return None
