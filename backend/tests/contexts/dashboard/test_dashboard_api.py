from datetime import UTC, date, datetime
from uuid import UUID

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from src.app_factory import create_app
from src.application.dashboard.service import (
    LabStatusCount,
    RecentDirection,
    RegistrarDashboard,
    RegistrarKpis,
    StatusCount,
    TimelineBucket,
)
from src.core.config import get_settings
from src.core.responses import ResponseMeta, SingleResponse
from src.presentation.http.access_control.dependencies import get_current_user_id
from src.presentation.http.dashboard import (
    get_dashboard_use_case,
    get_registrar_dashboard_use_case,
)

_REGISTRAR_ID = UUID("018f9a10-0000-7000-8000-000000000001")


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
                        "status_color": "indigo",
                        "count": 7,
                    },
                    {
                        "status_code": "completed",
                        "status_color": "green",
                        "count": 3,
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


class FakeRegistrarDashboardUseCase:
    async def summary(
        self,
        *,
        date_from: date,
        date_to: date,
        period: str,
    ) -> SingleResponse[RegistrarDashboard]:
        return SingleResponse(
            data=RegistrarDashboard(
                generated_at=datetime(2026, 7, 13, 10, 0, tzinfo=UTC),
                kpis=RegistrarKpis(
                    directions_draft=3,
                    samples_pending=5,
                    urgent_open=2,
                    directions_received_today=4,
                    samples_received_today=6,
                ),
                directions_by_status=[
                    StatusCount(
                        id=UUID("018f9a10-0000-7000-8000-0000000000b1"),
                        code="draft",
                        count=3,
                    ),
                    StatusCount(
                        id=UUID("018f9a10-0000-7000-8000-0000000000b2"),
                        code="registered",
                        count=8,
                    ),
                ],
                samples_by_status=[
                    StatusCount(
                        id=UUID("018f9a10-0000-7000-8000-0000000000c1"),
                        code="pending",
                        count=5,
                        color="amber",
                    ),
                    StatusCount(
                        id=UUID("018f9a10-0000-7000-8000-0000000000c2"),
                        code="completed",
                        count=9,
                        color="green",
                    ),
                ],
                samples_by_lab=[
                    LabStatusCount(
                        lab_id=UUID("018f9a10-0000-7000-8000-0000000000d1"),
                        lab_code="BAC",
                        lab_name="Бактериология",
                        status_code="registered",
                        status_color="indigo",
                        count=7,
                    ),
                    LabStatusCount(
                        lab_id=UUID("018f9a10-0000-7000-8000-0000000000d1"),
                        lab_code="BAC",
                        lab_name="Бактериология",
                        status_code="rejected",
                        status_color="red",
                        count=2,
                    ),
                ],
                recent_directions=[
                    RecentDirection(
                        id=UUID("018f9a10-0000-7000-8000-0000000000aa"),
                        year_no=2026,
                        base_no=17,
                        status_code="draft",
                        status_color="gray",
                        is_urgent=True,
                        received_at=datetime(2026, 7, 13, 9, 0, tzinfo=UTC),
                    ),
                ],
                timeline=[
                    TimelineBucket(
                        bucket_start=date(2026, 7, 12),
                        by_status={"pending": 3, "registered": 4, "rejected": 2},
                    ),
                    TimelineBucket(
                        bucket_start=date(2026, 7, 13),
                        by_status={"pending": 1, "completed": 5},
                    ),
                ],
            ),
            meta=ResponseMeta(operation="dashboard.registrar"),
        )


def _client(monkeypatch: MonkeyPatch, *, authenticate: bool = True) -> TestClient:
    monkeypatch.setenv("APP_DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
    monkeypatch.setenv("APP_JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("APP_AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("APP_AUTH_COOKIE_DOMAIN", "localhost")
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_dashboard_use_case] = lambda: FakeDashboardUseCase()
    app.dependency_overrides[get_registrar_dashboard_use_case] = (
        lambda: FakeRegistrarDashboardUseCase()
    )
    if authenticate:
        app.dependency_overrides[get_current_user_id] = lambda: _REGISTRAR_ID
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
        assert payload["data"]["samples_by_status"][0]["status_color"] == "indigo"
        assert payload["data"]["samples_by_status"][1]["status_code"] == "completed"
        assert payload["data"]["samples_by_status"][1]["status_color"] == "green"
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


def test_registrar_dashboard_endpoint_returns_intake_read_model(
    monkeypatch: MonkeyPatch,
) -> None:
    try:
        client = _client(monkeypatch)

        response = client.get(
            "/api/v1/dashboard/registrar",
            params={"date_from": "2026-06-29", "date_to": "2026-07-13", "period": "daily"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert set(payload) == {"data", "meta"}
        assert payload["meta"]["operation"] == "dashboard.registrar"
        data = payload["data"]
        assert data["kpis"]["directions_draft"] == 3
        assert data["kpis"]["samples_pending"] == 5
        assert data["kpis"]["urgent_open"] == 2
        assert data["kpis"]["directions_received_today"] == 4
        assert data["kpis"]["samples_received_today"] == 6
        assert data["directions_by_status"][0]["code"] == "draft"
        assert data["directions_by_status"][0]["id"] == "018f9a10-0000-7000-8000-0000000000b1"
        assert data["samples_by_status"][0]["code"] == "pending"
        assert data["samples_by_status"][1]["code"] == "completed"
        assert data["samples_by_status"][1]["color"] == "green"
        assert data["recent_directions"][0]["base_no"] == 17
        assert data["recent_directions"][0]["is_urgent"] is True
        assert data["recent_directions"][0]["status_color"] == "gray"
        assert data["timeline"][0]["bucket_start"] == "2026-07-12"
        assert data["timeline"][0]["by_status"]["registered"] == 4
        assert data["timeline"][0]["by_status"]["rejected"] == 2
        assert data["samples_by_lab"][0]["lab_name"] == "Бактериология"
        assert data["samples_by_lab"][0]["status_color"] == "indigo"
        assert data["samples_by_lab"][1]["status_code"] == "rejected"
    finally:
        get_settings.cache_clear()


def test_registrar_dashboard_requires_authentication(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch, authenticate=False)

        response = client.get(
            "/api/v1/dashboard/registrar",
            params={"date_from": "2026-06-29", "date_to": "2026-07-13"},
        )

        assert response.status_code == 401
    finally:
        get_settings.cache_clear()
