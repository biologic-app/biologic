from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from src.app_factory import create_app
from src.core.config import get_settings


def test_catalog_list_endpoint_has_list_envelope(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("APP_DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
    monkeypatch.setenv("APP_JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("APP_AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("APP_AUTH_COOKIE_DOMAIN", "localhost")
    get_settings.cache_clear()

    try:
        app = create_app()
        client = TestClient(app)

        response = client.get("/api/v1/branches")

        assert response.status_code in {200, 409}
        if response.status_code == 200:
            payload = response.json()
            assert set(payload) == {"items", "meta"}
            assert payload["meta"]["version"] == "v1"
    finally:
        get_settings.cache_clear()
