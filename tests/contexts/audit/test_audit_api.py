from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from src.app_factory import create_app
from src.contexts.audit.presentation.router import get_audit_repository
from src.core.config import get_settings
from src.core.pagination import PaginationParams
from src.infrastructure.db.models import ChangeLog

HISTORY_ID = UUID("00000000-0000-0000-0000-000000000001")
RESEARCH_ID = UUID("00000000-0000-0000-0000-000000000002")


class FakeAuditRepository:
    def __init__(self) -> None:
        self.params: PaginationParams | None = None

    async def list(self, params: PaginationParams) -> SimpleNamespace:
        self.params = params
        return SimpleNamespace(
            items=[
                ChangeLog(
                    id=HISTORY_ID,
                    entity_type="research",
                    entity_id=RESEARCH_ID,
                    action="research.update",
                    actor_name="api",
                    diff={
                        "recommendation": {
                            "from": "old recommendation",
                            "to": "new recommendation",
                        },
                    },
                    snapshot={"recommendation": "new recommendation"},
                    created_at=datetime(2026, 6, 9, 10, 0, tzinfo=UTC),
                ),
            ],
            total=1,
            has_more=False,
            next_cursor=None,
        )


def _client(monkeypatch: MonkeyPatch, repository: FakeAuditRepository) -> TestClient:
    monkeypatch.setenv("APP_DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
    monkeypatch.setenv("APP_JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("APP_AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("APP_AUTH_COOKIE_DOMAIN", "localhost")
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_audit_repository] = lambda: repository
    return TestClient(app)


def test_history_list_exposes_research_recommendation_diff(monkeypatch: MonkeyPatch) -> None:
    try:
        repository = FakeAuditRepository()
        client = _client(monkeypatch, repository)

        response = client.get(
            "/api/v1/history",
            params={
                "filters": (
                    '{"entity_type":"research",'
                    '"entity_id":"00000000-0000-0000-0000-000000000002"}'
                ),
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["items"][0]["entity_type"] == "research"
        assert payload["items"][0]["entity_id"] == str(RESEARCH_ID)
        assert payload["items"][0]["diff"]["recommendation"] == {
            "from": "old recommendation",
            "to": "new recommendation",
        }
        assert repository.params is not None
        assert repository.params.filters == (
            '{"entity_type":"research","entity_id":"00000000-0000-0000-0000-000000000002"}'
        )
    finally:
        get_settings.cache_clear()
