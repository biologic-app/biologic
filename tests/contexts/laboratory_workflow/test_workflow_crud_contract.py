from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from src.app_factory import create_app
from src.core.config import get_settings


def _client(monkeypatch: MonkeyPatch) -> TestClient:
    monkeypatch.setenv("APP_DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
    monkeypatch.setenv("APP_JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("APP_AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("APP_AUTH_COOKIE_DOMAIN", "localhost")
    get_settings.cache_clear()
    app = create_app()
    return TestClient(app)


def test_workflow_list_endpoint_has_list_envelope(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.get("/api/v1/directions")

        assert response.status_code == 200
        payload = response.json()
        assert set(payload) == {"items", "meta"}
        assert payload["meta"]["version"] == "v1"
    finally:
        get_settings.cache_clear()


def test_direction_create_uses_workflow_contract(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post(
            "/api/v1/directions",
            json={
                "year_no": 2026,
                "base_no": 17,
                "is_urgent": True,
                "object_id": "00000000-0000-0000-0000-000000000001",
            },
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["data"]["year_no"] == 2026
        assert payload["data"]["is_urgent"] is True
        assert payload["meta"]["operation"] == "directions.create"
    finally:
        get_settings.cache_clear()


def test_direction_create_rejects_catalog_only_field(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post("/api/v1/directions", json={"year_no": 2026, "code": "CAT"})

        assert response.status_code == 422
        payload = response.json()
        assert any(error["type"] == "extra_forbidden" for error in payload["errors"])
    finally:
        get_settings.cache_clear()


def test_workflow_patch_rejects_status_id(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.patch(
            "/api/v1/directions/00000000-0000-0000-0000-000000000001",
            json={"status_id": "00000000-0000-0000-0000-000000000002"},
        )

        assert response.status_code == 409
        payload = response.json()
        assert payload["code"] == "invalid_status_transition"
    finally:
        get_settings.cache_clear()


def test_sample_patch_rejects_status_id(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.patch(
            "/api/v1/samples/00000000-0000-0000-0000-000000000001",
            json={"status_id": "00000000-0000-0000-0000-000000000002"},
        )

        assert response.status_code == 409
        payload = response.json()
        assert payload["code"] == "invalid_status_transition"
    finally:
        get_settings.cache_clear()


def test_research_patch_rejects_status_id(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.patch(
            "/api/v1/research/00000000-0000-0000-0000-000000000001",
            json={"status_id": "00000000-0000-0000-0000-000000000002"},
        )

        assert response.status_code == 409
        payload = response.json()
        assert payload["code"] == "invalid_status_transition"
    finally:
        get_settings.cache_clear()


def test_test_patch_rejects_status_id(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.patch(
            "/api/v1/tests/00000000-0000-0000-0000-000000000001",
            json={"status_id": "00000000-0000-0000-0000-000000000002"},
        )

        assert response.status_code == 409
        payload = response.json()
        assert payload["code"] == "invalid_status_transition"
    finally:
        get_settings.cache_clear()


def test_tests_reject_generic_creation(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post(
            "/api/v1/tests",
            json={
                "research_id": "00000000-0000-0000-0000-000000000001",
                "indicator_id": "00000000-0000-0000-0000-000000000002",
            },
        )

        assert response.status_code == 409
        payload = response.json()
        assert payload["code"] == "resource_read_only"
    finally:
        get_settings.cache_clear()
