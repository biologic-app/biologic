from fastapi.testclient import TestClient
from pydantic import BaseModel
from pytest import MonkeyPatch

from src.app_factory import create_app
from src.contexts.catalogs.presentation.router import get_catalog_use_case
from src.contexts.laboratory_workflow.presentation.router import get_workflow_crud_use_case
from src.core.config import get_settings
from src.core.errors import DomainConflictError
from src.core.pagination import PageMeta, PaginationParams
from src.core.responses import ListResponse, ResponseMeta, SingleResponse


class FakeCatalogCrudUseCase:
    async def list_branches(self, params: PaginationParams) -> ListResponse[dict[str, object]]:
        return ListResponse(
            items=[],
            meta=PageMeta(
                total=0,
                limit=params.limit,
                has_more=False,
            ),
        )

    async def create_branch(self, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        return SingleResponse(
            data={"id": "00000000-0000-0000-0000-000000000001", **payload.model_dump()},
            meta=ResponseMeta(operation="branches.create"),
        )

    async def list_direction_statuses(
        self,
        params: PaginationParams,
    ) -> ListResponse[dict[str, object]]:
        return ListResponse(
            items=[],
            meta=PageMeta(
                total=0,
                limit=params.limit,
                has_more=False,
            ),
        )

    def reject_read_only_status_write(self, resource: str) -> None:
        raise DomainConflictError(
            code="resource_read_only",
            detail=f"{resource} cannot be changed through catalog CRUD.",
        )


class FakeWorkflowCrudUseCase:
    async def create_direction(self, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        return SingleResponse(
            data={"id": "00000000-0000-0000-0000-000000000001", **payload.model_dump()},
            meta=ResponseMeta(operation="directions.create"),
        )


def _client(monkeypatch: MonkeyPatch) -> TestClient:
    monkeypatch.setenv("APP_DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
    monkeypatch.setenv("APP_JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("APP_AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("APP_AUTH_COOKIE_DOMAIN", "localhost")
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_catalog_use_case] = lambda: FakeCatalogCrudUseCase()
    app.dependency_overrides[get_workflow_crud_use_case] = lambda: FakeWorkflowCrudUseCase()
    return TestClient(app)


def test_catalog_list_endpoint_has_list_envelope(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.get("/api/v1/branches")

        assert response.status_code in {200, 409}
        if response.status_code == 200:
            payload = response.json()
            assert set(payload) == {"items", "meta"}
            assert payload["meta"]["version"] == "v1"
    finally:
        get_settings.cache_clear()


def test_branch_create_accepts_only_branch_schema(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post("/api/v1/branches", json={"code": "MSK", "name": "Moscow"})

        assert response.status_code == 201
        payload = response.json()
        assert payload["data"]["code"] == "MSK"
        assert payload["data"]["name"] == "Moscow"
        assert payload["meta"]["operation"] == "branches.create"
    finally:
        get_settings.cache_clear()


def test_branch_create_rejects_unknown_fields(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post(
            "/api/v1/branches",
            json={"code": "MSK", "name": "Moscow", "status_id": "not-a-branch-field"},
        )

        assert response.status_code == 422
        payload = response.json()
        assert payload["status"] == 422
        assert any(error["type"] == "extra_forbidden" for error in payload["errors"])
    finally:
        get_settings.cache_clear()


def test_sample_type_create_rejects_missing_required_code(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post("/api/v1/sample_types", json={"name": "Water"})

        assert response.status_code == 422
        payload = response.json()
        assert payload["status"] == 422
        assert any(error["loc"][-1] == "code" for error in payload["errors"])
    finally:
        get_settings.cache_clear()


def test_status_resource_rejects_writes(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post(
            "/api/v1/direction_statuses",
            json={"code": "archived", "name": "Archived"},
        )

        assert response.status_code == 409
        payload = response.json()
        assert payload["code"] == "resource_read_only"
    finally:
        get_settings.cache_clear()


def test_status_resource_allows_reads(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.get("/api/v1/direction_statuses")

        assert response.status_code == 200
        payload = response.json()
        assert set(payload) == {"items", "meta"}
        assert payload["meta"]["version"] == "v1"
    finally:
        get_settings.cache_clear()


def test_catalog_router_does_not_accept_access_control_payloads(
    monkeypatch: MonkeyPatch,
) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post(
            "/api/v1/branches",
            json={
                "username": "admin",
                "password_hash": "hash",
                "role_id": "00000000-0000-0000-0000-000000000001",
            },
        )

        assert response.status_code == 422
        payload = response.json()
        assert payload["status"] == 422
    finally:
        get_settings.cache_clear()


def test_catalog_router_does_not_own_history(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post("/api/v1/history", json={"entity_type": "samples"})

        assert response.status_code == 405
    finally:
        get_settings.cache_clear()


def test_catalog_router_does_not_own_alerts(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post(
            "/api/v1/alerts",
            json={"user_id": "00000000-0000-0000-0000-000000000001"},
        )

        assert response.status_code == 405
    finally:
        get_settings.cache_clear()


def test_catalog_router_does_not_own_workflow_resources(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post("/api/v1/directions", json={"year_no": 2026})

        assert response.status_code == 201
        payload = response.json()
        assert payload["meta"]["operation"] == "directions.create"
    finally:
        get_settings.cache_clear()
