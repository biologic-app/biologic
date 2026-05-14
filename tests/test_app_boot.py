from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from src.app_factory import create_app
from src.core.config import get_settings


def test_app_boots_and_health_endpoint_returns_ok(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("APP_DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
    monkeypatch.setenv("APP_JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("APP_AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("APP_AUTH_COOKIE_DOMAIN", "localhost")

    get_settings.cache_clear()
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    get_settings.cache_clear()
