from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from src.app_factory import create_app
from src.contexts.laboratory_workflow.application.dto import (
    CommandResult,
    RegisterDirectionInput,
    RegisterSampleInput,
    RejectSampleInput,
    ResearchCommandInput,
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

    async def register_sample(self, command: RegisterSampleInput) -> CommandResult:
        return CommandResult(
            id=command.sample_id,
            status_id=UUID("00000000-0000-0000-0000-000000000004"),
            updated_at=datetime(2026, 5, 14, 11, 0, tzinfo=UTC),
        )

    async def reject_sample(self, command: RejectSampleInput) -> CommandResult:
        return CommandResult(
            id=command.sample_id,
            status_id=UUID("00000000-0000-0000-0000-000000000006"),
            updated_at=datetime(2026, 5, 14, 12, 0, tzinfo=UTC),
        )

    async def reject_research(self, command: ResearchCommandInput) -> CommandResult:
        return CommandResult(
            id=command.research_id,
            status_id=UUID("00000000-0000-0000-0000-000000000008"),
            updated_at=datetime(2026, 5, 14, 13, 0, tzinfo=UTC),
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


def test_register_sample_command_response_shape(monkeypatch: MonkeyPatch) -> None:
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
            "/api/v1/samples/00000000-0000-0000-0000-000000000005/register",
            json={
                "actor_id": "00000000-0000-0000-0000-000000000003",
                "received_at": "2026-05-14T10:00:00Z",
                "deadline": "2026-05-16T10:00:00Z",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["data"] == {
            "id": "00000000-0000-0000-0000-000000000005",
            "status_id": "00000000-0000-0000-0000-000000000004",
            "updated_at": "2026-05-14T11:00:00Z",
        }
        assert payload["meta"]["operation"] == "samples.register"
    finally:
        get_settings.cache_clear()


def test_register_sample_rejects_naive_received_at(monkeypatch: MonkeyPatch) -> None:
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
            "/api/v1/samples/00000000-0000-0000-0000-000000000005/register",
            json={
                "actor_id": "00000000-0000-0000-0000-000000000003",
                "received_at": "2026-05-14T10:00:00",
                "deadline": "2026-05-16T10:00:00Z",
            },
        )

        assert response.status_code == 422
        payload = response.json()
        assert payload["status"] == 422
        assert "timestamp must be timezone-aware" in str(payload)
    finally:
        get_settings.cache_clear()


def test_register_sample_rejects_naive_deadline(monkeypatch: MonkeyPatch) -> None:
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
            "/api/v1/samples/00000000-0000-0000-0000-000000000005/register",
            json={
                "actor_id": "00000000-0000-0000-0000-000000000003",
                "received_at": "2026-05-14T10:00:00Z",
                "deadline": "2026-05-16T10:00:00",
            },
        )

        assert response.status_code == 422
        payload = response.json()
        assert payload["status"] == 422
        assert "timestamp must be timezone-aware" in str(payload)
    finally:
        get_settings.cache_clear()


def test_reject_sample_command_response_shape(monkeypatch: MonkeyPatch) -> None:
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
            "/api/v1/samples/00000000-0000-0000-0000-000000000005/reject",
            json={
                "actor_id": "00000000-0000-0000-0000-000000000003",
                "reason": "Container damaged",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["data"] == {
            "id": "00000000-0000-0000-0000-000000000005",
            "status_id": "00000000-0000-0000-0000-000000000006",
            "updated_at": "2026-05-14T12:00:00Z",
        }
        assert payload["meta"]["operation"] == "samples.reject"
    finally:
        get_settings.cache_clear()


def test_reject_research_command_response_shape(monkeypatch: MonkeyPatch) -> None:
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
            "/api/v1/research/00000000-0000-0000-0000-000000000007/reject",
            json={
                "actor_id": "00000000-0000-0000-0000-000000000003",
                "reason": "Исследование отклонено",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["data"] == {
            "id": "00000000-0000-0000-0000-000000000007",
            "status_id": "00000000-0000-0000-0000-000000000008",
            "updated_at": "2026-05-14T13:00:00Z",
        }
        assert payload["meta"]["operation"] == "research.reject"
    finally:
        get_settings.cache_clear()
