from uuid import UUID

import httpx
from fastapi import FastAPI
from pydantic import BaseModel
from pytest import MonkeyPatch

from src.app_factory import create_app
from src.contexts.laboratory_workflow.presentation.router import get_workflow_crud_use_case
from src.core.config import get_settings
from src.core.errors import DomainConflictError
from src.core.pagination import PageMeta, PaginationParams, get_pagination_params
from src.core.responses import ListResponse, ResponseMeta, SingleResponse
from src.presentation.http.catalogs.dependencies import (
    get_branch_use_case,
    get_direction_status_use_case,
)


class FakeBranchUseCase:
    async def list(self, params: PaginationParams) -> ListResponse[dict[str, object]]:
        return ListResponse(
            items=[],
            meta=PageMeta(
                total=0,
                limit=params.limit,
                has_more=False,
            ),
        )

    async def create(self, payload: BaseModel) -> SingleResponse[dict[str, object]]:
        return SingleResponse(
            data={"id": "00000000-0000-0000-0000-000000000001", **payload.model_dump()},
            meta=ResponseMeta(operation="branches.create"),
        )


class FakeDirectionStatusUseCase:
    async def list(
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

    async def update(
        self,
        item_id: UUID,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        return SingleResponse(
            data={
                "id": str(item_id),
                "code": "draft",
                "name": payload.model_dump()["name"],
            },
            meta=ResponseMeta(operation="direction_statuses.update"),
        )

    def reject_write(self) -> None:
        raise DomainConflictError(
            code="resource_read_only",
            detail="direction_statuses cannot be changed through catalog CRUD.",
        )


class FakeWorkflowCrudUseCase:
    async def create_direction(
        self, payload: BaseModel, *, actor_id: UUID | None = None
    ) -> SingleResponse[dict[str, object]]:
        return SingleResponse(
            data={"id": "00000000-0000-0000-0000-000000000001", **payload.model_dump()},
            meta=ResponseMeta(operation="directions.create"),
        )


def _app(monkeypatch: MonkeyPatch) -> FastAPI:
    monkeypatch.setenv("APP_DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
    monkeypatch.setenv("APP_JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("APP_AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("APP_AUTH_COOKIE_DOMAIN", "localhost")
    get_settings.cache_clear()
    app = create_app()

    async def override_branch_use_case() -> FakeBranchUseCase:
        return FakeBranchUseCase()

    async def override_direction_status_use_case() -> FakeDirectionStatusUseCase:
        return FakeDirectionStatusUseCase()

    async def override_workflow_crud_use_case() -> FakeWorkflowCrudUseCase:
        return FakeWorkflowCrudUseCase()

    async def override_pagination_params() -> PaginationParams:
        return PaginationParams()

    app.dependency_overrides[get_branch_use_case] = override_branch_use_case
    app.dependency_overrides[get_direction_status_use_case] = override_direction_status_use_case
    app.dependency_overrides[get_workflow_crud_use_case] = override_workflow_crud_use_case
    app.dependency_overrides[get_pagination_params] = override_pagination_params
    return app


async def _request(
    monkeypatch: MonkeyPatch,
    method: str,
    path: str,
    *,
    json: dict[str, object] | None = None,
) -> httpx.Response:
    try:
        transport = httpx.ASGITransport(app=_app(monkeypatch))
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.request(method, path, json=json)
    finally:
        get_settings.cache_clear()


async def test_catalog_list_endpoint_has_list_envelope(monkeypatch: MonkeyPatch) -> None:
    response = await _request(monkeypatch, "GET", "/api/v1/branches")

    assert response.status_code in {200, 409}
    if response.status_code == 200:
        payload = response.json()
        assert set(payload) == {"items", "meta"}
        assert payload["meta"]["version"] == "v1"


async def test_branch_create_accepts_only_branch_schema(monkeypatch: MonkeyPatch) -> None:
    response = await _request(
        monkeypatch,
        "POST",
        "/api/v1/branches",
        json={"code": "MSK", "name": "Moscow"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["data"]["code"] == "MSK"
    assert payload["data"]["name"] == "Moscow"
    assert payload["meta"]["operation"] == "branches.create"


async def test_branch_create_rejects_unknown_fields(monkeypatch: MonkeyPatch) -> None:
    response = await _request(
        monkeypatch,
        "POST",
        "/api/v1/branches",
        json={"code": "MSK", "name": "Moscow", "status_id": "not-a-branch-field"},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["status"] == 422
    assert any(error["type"] == "extra_forbidden" for error in payload["errors"])


async def test_sample_type_create_rejects_missing_required_code(
    monkeypatch: MonkeyPatch,
) -> None:
    response = await _request(
        monkeypatch,
        "POST",
        "/api/v1/sample_types",
        json={"name": "Water"},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["status"] == 422
    assert any(error["loc"][-1] == "code" for error in payload["errors"])


async def test_status_resource_rejects_writes(monkeypatch: MonkeyPatch) -> None:
    response = await _request(
        monkeypatch,
        "POST",
        "/api/v1/direction_statuses",
        json={"code": "archived", "name": "Archived"},
    )

    assert response.status_code == 409
    payload = response.json()
    assert payload["code"] == "resource_read_only"


async def test_status_resource_allows_name_update(monkeypatch: MonkeyPatch) -> None:
    response = await _request(
        monkeypatch,
        "PATCH",
        "/api/v1/direction_statuses/00000000-0000-0000-0000-000000000001",
        json={"name": "Черновик"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["code"] == "draft"
    assert payload["data"]["name"] == "Черновик"
    assert payload["meta"]["operation"] == "direction_statuses.update"


async def test_status_resource_rejects_code_update(monkeypatch: MonkeyPatch) -> None:
    response = await _request(
        monkeypatch,
        "PATCH",
        "/api/v1/direction_statuses/00000000-0000-0000-0000-000000000001",
        json={"code": "renamed", "name": "Renamed"},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["status"] == 422
    assert any(error["type"] == "extra_forbidden" for error in payload["errors"])


async def test_status_resource_rejects_delete(monkeypatch: MonkeyPatch) -> None:
    response = await _request(
        monkeypatch,
        "DELETE",
        "/api/v1/direction_statuses/00000000-0000-0000-0000-000000000001",
    )

    assert response.status_code == 409
    payload = response.json()
    assert payload["code"] == "resource_read_only"


async def test_status_resource_allows_reads(monkeypatch: MonkeyPatch) -> None:
    response = await _request(monkeypatch, "GET", "/api/v1/direction_statuses")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"items", "meta"}
    assert payload["meta"]["version"] == "v1"


async def test_catalog_router_does_not_accept_access_control_payloads(
    monkeypatch: MonkeyPatch,
) -> None:
    response = await _request(
        monkeypatch,
        "POST",
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


async def test_catalog_router_does_not_own_history(monkeypatch: MonkeyPatch) -> None:
    response = await _request(
        monkeypatch,
        "POST",
        "/api/v1/history",
        json={"entity_type": "samples"},
    )

    assert response.status_code == 405


async def test_catalog_router_does_not_own_alerts(monkeypatch: MonkeyPatch) -> None:
    response = await _request(
        monkeypatch,
        "POST",
        "/api/v1/alerts",
        json={"user_id": "00000000-0000-0000-0000-000000000001"},
    )

    assert response.status_code == 405


async def test_catalog_router_does_not_own_workflow_resources(
    monkeypatch: MonkeyPatch,
) -> None:
    response = await _request(
        monkeypatch,
        "POST",
        "/api/v1/directions",
        json={"year_no": 2026},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["meta"]["operation"] == "directions.create"
