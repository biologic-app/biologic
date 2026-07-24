from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from src.app_factory import create_app
from src.application.workflows.use_cases.template_crud import WorkflowTemplateUseCase
from src.core.config import get_settings
from src.core.responses import ResponseMeta, SingleResponse
from src.presentation.http.workflows.dependencies import (
    get_execute_step_use_case,
    get_template_use_case,
)


def _configure(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("APP_DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
    monkeypatch.setenv("APP_JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("APP_AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("APP_AUTH_COOKIE_DOMAIN", "localhost")
    get_settings.cache_clear()


class _FakeTemplateUseCase:
    async def create(self, payload: Any) -> SingleResponse[dict[str, object]]:
        return SingleResponse(
            data={"id": "00000000-0000-0000-0000-0000000000d1", "title": payload.title},
            meta=ResponseMeta(operation="workflows.templates.create"),
        )


class _FakeExecuteStepUseCase:
    async def execute(self, command: Any) -> SingleResponse[dict[str, object]]:
        return SingleResponse(
            data={
                "status": "applied",
                "already_applied": False,
                "node_id": command.node_id,
                "attempt": command.attempt,
                "results": [],
            },
            meta=ResponseMeta(operation="workflows.execute_step"),
        )


def test_create_template_response_shape(monkeypatch: MonkeyPatch) -> None:
    _configure(monkeypatch)
    try:
        app = create_app()
        app.dependency_overrides[get_template_use_case] = lambda: _FakeTemplateUseCase()
        client = TestClient(app)

        response = client.post("/api/v1/workflow-templates", json={"title": "Microbiology"})

        assert response.status_code == 201
        payload = response.json()
        assert payload["data"]["title"] == "Microbiology"
        assert payload["meta"]["operation"] == "workflows.templates.create"
    finally:
        get_settings.cache_clear()


def test_execute_step_response_shape(monkeypatch: MonkeyPatch) -> None:
    _configure(monkeypatch)
    try:
        app = create_app()
        app.dependency_overrides[get_execute_step_use_case] = lambda: _FakeExecuteStepUseCase()
        client = TestClient(app)

        response = client.post(
            "/api/v1/workflow-runs/00000000-0000-0000-0000-0000000000e1/execute-step",
            json={
                "node_id": "n2",
                "attempt": 1,
                "actions": [
                    {
                        "action_id": "a1",
                        "command": "tests.complete",
                        "resolved_args": {"test_id": "00000000-0000-0000-0000-0000000000e2"},
                    }
                ],
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["data"]["status"] == "applied"
        assert payload["meta"]["operation"] == "workflows.execute_step"
    finally:
        get_settings.cache_clear()


def test_create_version_rejects_invalid_schema(monkeypatch: MonkeyPatch) -> None:
    _configure(monkeypatch)
    try:
        app = create_app()
        # A real use case: validation runs before the UoW is ever entered, so the
        # dummy factory (which would fail if used) proves the 422 is pre-UoW.
        app.dependency_overrides[get_template_use_case] = lambda: WorkflowTemplateUseCase(
            uow_factory=_never_called
        )
        client = TestClient(app)

        response = client.post(
            "/api/v1/workflow-templates/00000000-0000-0000-0000-0000000000f1/versions",
            json={"formatVersion": 1, "title": "x", "nodes": [], "edges": []},
        )

        assert response.status_code == 422
        assert response.json()["status"] == 422
    finally:
        get_settings.cache_clear()


def _never_called() -> Any:
    raise AssertionError("UoW must not be entered for an invalid schema.")
