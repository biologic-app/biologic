from fastapi.testclient import TestClient
from pydantic import BaseModel
from pytest import MonkeyPatch

from src.app_factory import create_app
from src.contexts.access_control.presentation.router import get_access_control_use_case
from src.core.config import get_settings
from src.core.pagination import PageMeta, PaginationParams
from src.core.responses import ListResponse, ResponseMeta, SingleResponse


class FakeAccessControlCrudUseCase:
    async def list_users(self, params: PaginationParams) -> ListResponse[dict[str, object]]:
        return ListResponse(
            items=[],
            meta=PageMeta(
                total=0,
                limit=params.limit,
                has_more=False,
            ),
        )

    async def create_user(self, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        data = payload.model_dump()
        data.pop("password_hash", None)
        return SingleResponse(
            data={"id": "00000000-0000-0000-0000-000000000001", **data},
            meta=ResponseMeta(operation="users.create"),
        )

    async def create_permission(self, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        return SingleResponse(
            data={"id": "00000000-0000-0000-0000-000000000001", **payload.model_dump()},
            meta=ResponseMeta(operation="permissions.create"),
        )


def _client(monkeypatch: MonkeyPatch) -> TestClient:
    monkeypatch.setenv("APP_DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
    monkeypatch.setenv("APP_JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("APP_AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("APP_AUTH_COOKIE_DOMAIN", "localhost")
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_access_control_use_case] = lambda: FakeAccessControlCrudUseCase()
    return TestClient(app)


def test_access_control_list_endpoint_has_list_envelope(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.get("/api/v1/users")

        assert response.status_code == 200
        payload = response.json()
        assert set(payload) == {"items", "meta"}
        assert payload["meta"]["version"] == "v1"
    finally:
        get_settings.cache_clear()


def test_user_create_uses_access_control_contract(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post(
            "/api/v1/users",
            json={
                "username": "admin",
                "password_hash": "hash",
                "role_id": "00000000-0000-0000-0000-000000000001",
                "lab_id": "00000000-0000-0000-0000-000000000002",
                "is_registrar": True,
            },
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["data"]["username"] == "admin"
        assert payload["data"]["is_registrar"] is True
        assert payload["meta"]["operation"] == "users.create"
    finally:
        get_settings.cache_clear()


def test_user_create_rejects_catalog_only_fields(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post(
            "/api/v1/users",
            json={
                "username": "admin",
                "password_hash": "hash",
                "role_id": "00000000-0000-0000-0000-000000000001",
                "full_name": "Catalog field",
            },
        )

        assert response.status_code == 422
        payload = response.json()
        assert payload["status"] == 422
        assert any(error["type"] == "extra_forbidden" for error in payload["errors"])
    finally:
        get_settings.cache_clear()


def test_role_create_validates_scope_type(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post("/api/v1/roles", json={"key": "auditor", "name": "Auditor"})

        assert response.status_code == 422
        payload = response.json()
        assert any(error["loc"][-1] == "scope_type" for error in payload["errors"])
    finally:
        get_settings.cache_clear()


def test_permission_create_uses_access_control_contract(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post(
            "/api/v1/permissions",
            json={"resource": "directions", "action": "read"},
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["data"]["resource"] == "directions"
        assert payload["data"]["action"] == "read"
        assert payload["meta"]["operation"] == "permissions.create"
    finally:
        get_settings.cache_clear()
