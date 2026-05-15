from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from src.app_factory import create_app
from src.contexts.laboratory_workflow.application.dto import (
    CommandResult,
    RegisterDirectionInput,
)
from src.contexts.laboratory_workflow.presentation.router import get_workflow_command_service
from src.core.config import get_settings


class FakeWorkflowCommandService:
    async def register_direction(self, command: RegisterDirectionInput) -> CommandResult:
        return CommandResult(
            id=command.direction_id,
            status_id=UUID("00000000-0000-0000-0000-000000000002"),
            updated_at=datetime(2026, 5, 14, 10, 0, tzinfo=UTC),
        )


def test_register_direction_command_response_shape(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("APP_DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
    monkeypatch.setenv("APP_JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("APP_AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("APP_AUTH_COOKIE_DOMAIN", "localhost")
    get_settings.cache_clear()

    try:
        app = create_app()
        app.dependency_overrides[get_workflow_command_service] = (
            lambda: FakeWorkflowCommandService()
        )
        client = TestClient(app)

        response = client.post(
            "/api/v1/directions/00000000-0000-0000-0000-000000000001/register",
            json={
                "actor_id": "00000000-0000-0000-0000-000000000003",
                "comment": "Ready for laboratory workflow",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["data"] == {
            "id": "00000000-0000-0000-0000-000000000001",
            "status_id": "00000000-0000-0000-0000-000000000002",
            "updated_at": "2026-05-14T10:00:00Z",
        }
        assert payload["meta"]["operation"] == "directions.register"
    finally:
        get_settings.cache_clear()
