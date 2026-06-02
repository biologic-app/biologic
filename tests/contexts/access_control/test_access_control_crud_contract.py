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

    async def read_role_permissions(self, role_id: object) -> SingleResponse[dict[str, object]]:
        return SingleResponse(
            data={
                "permissions": [
                    {
                        "id": "00000000-0000-0000-0000-000000000010",
                        "resource": "samples",
                        "action": "view",
                        "scope": "own_lab",
                    }
                ],
            },
            meta=ResponseMeta(operation="roles.permissions.read"),
        )

    async def replace_role_permissions(
        self,
        role_id: object,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        return SingleResponse(
            data=payload.model_dump(),
            meta=ResponseMeta(operation="roles.permissions.replace"),
        )

    async def read_user_permissions(self, user_id: object) -> SingleResponse[dict[str, object]]:
        return SingleResponse(
            data={
                "permissions": [
                    {
                        "id": "00000000-0000-0000-0000-000000000011",
                        "resource": "users",
                        "action": "view",
                        "scope": "all",
                    }
                ],
            },
            meta=ResponseMeta(operation="users.permissions.read"),
        )

    async def read_user_permission_overrides(
        self,
        user_id: object,
    ) -> SingleResponse[dict[str, object]]:
        return SingleResponse(
            data={
                "overrides": [
                    {
                        "permission_id": "00000000-0000-0000-0000-000000000012",
                        "resource": "users",
                        "action": "delete",
                        "allowed": False,
                        "scope": None,
                    }
                ],
            },
            meta=ResponseMeta(operation="users.overrides.read"),
        )

    async def replace_user_permission_overrides(
        self,
        user_id: object,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        return SingleResponse(
            data=payload.model_dump(),
            meta=ResponseMeta(operation="users.overrides.replace"),
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


def test_role_permissions_are_exposed_as_role_aggregate(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.get("/api/v1/roles/00000000-0000-0000-0000-000000000001/permissions")

        assert response.status_code == 200
        payload = response.json()
        assert payload["data"]["permissions"] == [
            {
                "id": "00000000-0000-0000-0000-000000000010",
                "resource": "samples",
                "action": "view",
                "scope": "own_lab",
            }
        ]
        assert payload["meta"]["operation"] == "roles.permissions.read"
    finally:
        get_settings.cache_clear()


def test_role_permissions_replace_allow_set_with_scope(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.put(
            "/api/v1/roles/00000000-0000-0000-0000-000000000001/permissions",
            json={
                "permissions": [
                    {
                        "permission_id": "00000000-0000-0000-0000-000000000010",
                        "scope": "own_branch",
                    }
                ],
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["data"]["permissions"][0]["scope"] == "own_branch"
        assert payload["meta"]["operation"] == "roles.permissions.replace"
    finally:
        get_settings.cache_clear()


def test_user_permissions_return_effective_permissions(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.get("/api/v1/users/00000000-0000-0000-0000-000000000001/permissions")

        assert response.status_code == 200
        payload = response.json()
        assert payload["data"]["permissions"][0]["resource"] == "users"
        assert payload["data"]["permissions"][0]["scope"] == "all"
        assert payload["meta"]["operation"] == "users.permissions.read"
    finally:
        get_settings.cache_clear()


def test_user_permission_overrides_are_separate_from_effective_permissions(
    monkeypatch: MonkeyPatch,
) -> None:
    try:
        client = _client(monkeypatch)

        response = client.get("/api/v1/users/00000000-0000-0000-0000-000000000001/overrides")

        assert response.status_code == 200
        payload = response.json()
        assert payload["data"]["overrides"][0]["allowed"] is False
        assert payload["data"]["overrides"][0]["scope"] is None
        assert payload["meta"]["operation"] == "users.overrides.read"
    finally:
        get_settings.cache_clear()


def test_user_permission_overrides_replace_allow_and_deny_rules(
    monkeypatch: MonkeyPatch,
) -> None:
    try:
        client = _client(monkeypatch)

        response = client.put(
            "/api/v1/users/00000000-0000-0000-0000-000000000001/overrides",
            json={
                "overrides": [
                    {
                        "permission_id": "00000000-0000-0000-0000-000000000012",
                        "allowed": True,
                        "scope": "all_branches",
                    },
                    {
                        "permission_id": "00000000-0000-0000-0000-000000000013",
                        "allowed": False,
                        "scope": None,
                    },
                ],
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["data"]["overrides"][0]["scope"] == "all_branches"
        assert payload["data"]["overrides"][1]["allowed"] is False
        assert payload["meta"]["operation"] == "users.overrides.replace"
    finally:
        get_settings.cache_clear()


def test_current_user_permissions_use_actor_identity(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.get(
            "/api/v1/user/me/permissions",
            headers={"X-Actor-Id": "00000000-0000-0000-0000-000000000001"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["data"]["permissions"][0]["action"] == "view"
        assert payload["meta"]["operation"] == "users.permissions.read"
    finally:
        get_settings.cache_clear()
