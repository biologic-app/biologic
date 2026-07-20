from typing import Any

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from src.app_factory import create_app
from src.core.config import get_settings
from src.core.responses import ResponseMeta, SingleResponse
from src.presentation.http.released_samples import get_released_samples_use_case


class FakeReleasedSamplesUseCase:
    async def released_by_direction(self) -> SingleResponse[list[dict[str, Any]]]:
        return SingleResponse(
            data=[
                {
                    "direction": {
                        "id": "00000000-0000-0000-0000-0000000000a1",
                        "year_no": 2026,
                        "base_no": 10,
                        "doctor": "Иванов Иван",
                        "object": {"name": "Ферма №1", "code": "F1"},
                    },
                    "samples": [
                        {
                            "id": "00000000-0000-0000-0000-000000000b01",
                            "name": "Проба 1",
                            "status_code": "completed",
                            "status_name": "Закрыт",
                            "sample_type_name": "Молоко",
                            "protocol_id": None,
                            "completed_at": "2026-07-15T00:00:00Z",
                        },
                    ],
                    "released_count": 1,
                    "total_count": 1,
                    "all_released": True,
                }
            ],
            meta=ResponseMeta(operation="directions.released_samples"),
        )


def _client(monkeypatch: MonkeyPatch) -> TestClient:
    monkeypatch.setenv("APP_DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
    monkeypatch.setenv("APP_JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("APP_AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("APP_AUTH_COOKIE_DOMAIN", "localhost")
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_released_samples_use_case] = lambda: FakeReleasedSamplesUseCase()
    return TestClient(app)


def test_released_samples_endpoint_returns_grouped_projection(
    monkeypatch: MonkeyPatch,
) -> None:
    try:
        client = _client(monkeypatch)

        response = client.get("/api/v1/directions/released-samples")

        assert response.status_code == 200
        payload = response.json()
        assert set(payload) == {"data", "meta"}
        assert payload["meta"]["operation"] == "directions.released_samples"
        group = payload["data"][0]
        assert group["all_released"] is True
        assert group["released_count"] == 1
        assert group["total_count"] == 1
        assert group["direction"]["object"]["code"] == "F1"
        assert group["samples"][0]["status_code"] == "completed"
    finally:
        get_settings.cache_clear()
