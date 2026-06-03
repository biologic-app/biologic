from datetime import UTC, date, datetime

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from src.app_factory import create_app
from src.contexts.dashboard.presentation.router import get_dashboard_use_case
from src.core.config import get_settings
from src.core.responses import ResponseMeta, SingleResponse


class FakeDashboardUseCase:
    async def summary(
        self,
        *,
        date_from: date,
        date_to: date,
        period: str,
    ) -> SingleResponse[dict[str, object]]:
        return SingleResponse(
            data={
                "period": period,
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
                "updated_at": "2026-06-03T10:00:00Z",
                "kpis": [
                    {
                        "key": "samples_received",
                        "label": "Поступило образцов",
                        "value": 42,
                        "unit": "count",
                    },
                    {
                        "key": "avg_turnaround_minutes",
                        "label": "Среднее время",
                        "value": 180,
                        "unit": "minutes",
                    },
                ],
                "timeline": [
                    {
                        "bucket_start": "2026-05-04",
                        "samples_received": 12,
                        "samples_completed": 8,
                        "samples_rejected": 1,
                        "tests_completed": 31,
                    },
                ],
                "samples_by_status": [
                    {
                        "status_code": "registered",
                        "status_name": "Зарегистрирован",
                        "count": 7,
                    },
                ],
                "research_by_lab": [
                    {
                        "lab_id": "00000000-0000-0000-0000-000000000001",
                        "lab_name": "Испытательная лаборатория",
                        "active_count": 5,
                        "completed_count": 9,
                    },
                ],
                "sample_types": [
                    {
                        "sample_type_id": "00000000-0000-0000-0000-000000000002",
                        "sample_type_name": "Молоко",
                        "count": 14,
                    },
                ],
            },
            meta=ResponseMeta(
                operation="dashboard.summary",
                timestamp=datetime(2026, 6, 3, 10, 0, tzinfo=UTC).isoformat(),
            ),
        )


def _client(monkeypatch: MonkeyPatch) -> TestClient:
    monkeypatch.setenv("APP_DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
    monkeypatch.setenv("APP_JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("APP_AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("APP_AUTH_COOKIE_DOMAIN", "localhost")
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_dashboard_use_case] = lambda: FakeDashboardUseCase()
    return TestClient(app)


def test_dashboard_summary_endpoint_returns_operational_read_model(
    monkeypatch: MonkeyPatch,
) -> None:
    try:
        client = _client(monkeypatch)

        response = client.get(
            "/api/v1/dashboard/summary",
            params={
                "date_from": "2026-05-01",
                "date_to": "2026-05-31",
                "period": "weekly",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert set(payload) == {"data", "meta"}
        assert payload["meta"]["operation"] == "dashboard.summary"
        assert payload["data"]["period"] == "weekly"
        assert payload["data"]["date_from"] == "2026-05-01"
        assert payload["data"]["date_to"] == "2026-05-31"
        assert payload["data"]["kpis"][0]["key"] == "samples_received"
        assert payload["data"]["timeline"][0]["bucket_start"] == "2026-05-04"
        assert payload["data"]["samples_by_status"][0]["status_code"] == "registered"
        assert payload["data"]["research_by_lab"][0]["active_count"] == 5
        assert payload["data"]["sample_types"][0]["count"] == 14
    finally:
        get_settings.cache_clear()


def test_dashboard_summary_rejects_unknown_period(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.get(
            "/api/v1/dashboard/summary",
            params={
                "date_from": "2026-05-01",
                "date_to": "2026-05-31",
                "period": "quarterly",
            },
        )

        assert response.status_code == 422
    finally:
        get_settings.cache_clear()
