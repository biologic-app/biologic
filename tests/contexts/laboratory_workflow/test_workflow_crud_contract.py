from uuid import UUID

from fastapi.testclient import TestClient
from pydantic import BaseModel
from pytest import MonkeyPatch

from src.app_factory import create_app
from src.contexts.laboratory_workflow.presentation.router import get_workflow_crud_use_case
from src.core.config import get_settings
from src.core.errors import DomainConflictError, NotFoundError
from src.core.pagination import PageMeta, PaginationParams
from src.core.responses import ListResponse, ResponseMeta, SingleResponse

_DRAFT_DIRECTION_ID = UUID("00000000-0000-0000-0000-000000000010")
_REGISTERED_DIRECTION_ID = UUID("00000000-0000-0000-0000-000000000011")
_MISSING_DIRECTION_ID = UUID("00000000-0000-0000-0000-000000000012")


class FakeWorkflowCrudUseCase:
    async def list_directions(self, params: PaginationParams) -> ListResponse[dict[str, object]]:
        return ListResponse(
            items=[],
            meta=PageMeta(
                total=0,
                limit=params.limit,
                has_more=False,
            ),
        )

    async def create_direction(
        self, payload: BaseModel, *, actor_id: UUID | None = None
    ) -> SingleResponse[dict[str, object]]:
        return SingleResponse(
            data={"id": "00000000-0000-0000-0000-000000000001", **payload.model_dump()},
            meta=ResponseMeta(operation="directions.create"),
        )

    async def update_direction(
        self,
        direction_id: object,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        data = payload.model_dump(exclude_unset=True)
        if "status_id" in data:
            raise DomainConflictError(
                code="invalid_status_transition",
                detail="directions lifecycle status must be changed through commands.",
            )
        return SingleResponse(data={"id": str(direction_id), **data}, meta=ResponseMeta())

    async def update_sample(
        self,
        sample_id: object,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        data = payload.model_dump(exclude_unset=True)
        if "status_id" in data:
            raise DomainConflictError(
                code="invalid_status_transition",
                detail="samples lifecycle status must be changed through commands.",
            )
        return SingleResponse(data={"id": str(sample_id), **data}, meta=ResponseMeta())

    async def update_research(
        self,
        research_id: object,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        data = payload.model_dump(exclude_unset=True)
        if "status_id" in data:
            raise DomainConflictError(
                code="invalid_status_transition",
                detail="research lifecycle status must be changed through commands.",
            )
        return SingleResponse(data={"id": str(research_id), **data}, meta=ResponseMeta())

    async def update_test(
        self,
        test_id: object,
        payload: BaseModel,
    ) -> SingleResponse[dict[str, object]]:
        data = payload.model_dump(exclude_unset=True)
        if "status_id" in data:
            raise DomainConflictError(
                code="invalid_status_transition",
                detail="tests lifecycle status must be changed through commands.",
            )
        return SingleResponse(data={"id": str(test_id), **data}, meta=ResponseMeta())

    async def import_directions(
        self,
        filename: str,
        content: bytes,
        *,
        type_: str,
        actor_id: UUID | None = None,
    ) -> SingleResponse[dict[str, object]]:
        return SingleResponse(
            data={
                "filename": filename,
                "type": type_,
                "actor_id": str(actor_id) if actor_id else None,
                "directions_created": 1,
                "samples_created": 1 if content else 0,
                "research_created": 0,
                "skipped": 0,
                "errors": [],
                "warnings": [],
            },
            meta=ResponseMeta(operation="directions.import"),
        )

    async def add_direction_sample(
        self,
        direction_id: UUID,
        payload: BaseModel,
        *,
        actor_id: UUID | None = None,
    ) -> SingleResponse[dict[str, object]]:
        if direction_id == _MISSING_DIRECTION_ID:
            raise NotFoundError(f"directions item {direction_id} was not found.")
        if direction_id != _DRAFT_DIRECTION_ID:
            raise DomainConflictError(
                code="direction_not_draft",
                detail="Direction can be modified only in draft status.",
            )
        data = payload.model_dump(exclude_unset=True)
        data["direction_id"] = str(direction_id)
        return SingleResponse(
            data={"id": "00000000-0000-0000-0000-000000000099", **data},
            meta=ResponseMeta(operation="samples.create"),
        )


def _client(monkeypatch: MonkeyPatch) -> TestClient:
    monkeypatch.setenv("APP_DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
    monkeypatch.setenv("APP_JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("APP_AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("APP_AUTH_COOKIE_DOMAIN", "localhost")
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_workflow_crud_use_case] = lambda: FakeWorkflowCrudUseCase()
    return TestClient(app)


def test_workflow_list_endpoint_has_list_envelope(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.get("/api/v1/directions")

        assert response.status_code == 200
        payload = response.json()
        assert set(payload) == {"items", "meta"}
        assert payload["meta"]["version"] == "v1"
    finally:
        get_settings.cache_clear()


def test_workflow_list_rejects_offset_pagination(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.get("/api/v1/directions?offset=0")

        assert response.status_code == 400
        assert "cursor" in response.json()["detail"]
    finally:
        get_settings.cache_clear()


def test_direction_create_uses_workflow_contract(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post(
            "/api/v1/directions",
            json={
                "year_no": 2026,
                "base_no": 17,
                "is_urgent": True,
                "object_id": "00000000-0000-0000-0000-000000000001",
            },
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["data"]["year_no"] == 2026
        assert payload["data"]["is_urgent"] is True
        assert payload["meta"]["operation"] == "directions.create"
    finally:
        get_settings.cache_clear()


def test_direction_create_rejects_catalog_only_field(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post("/api/v1/directions", json={"year_no": 2026, "code": "CAT"})

        assert response.status_code == 422
        payload = response.json()
        assert any(error["type"] == "extra_forbidden" for error in payload["errors"])
    finally:
        get_settings.cache_clear()


def test_workflow_patch_rejects_status_id(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.patch(
            "/api/v1/directions/00000000-0000-0000-0000-000000000001",
            json={"status_id": "00000000-0000-0000-0000-000000000002"},
        )

        assert response.status_code == 409
        payload = response.json()
        assert payload["code"] == "invalid_status_transition"
    finally:
        get_settings.cache_clear()


def test_sample_patch_rejects_status_id(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.patch(
            "/api/v1/samples/00000000-0000-0000-0000-000000000001",
            json={"status_id": "00000000-0000-0000-0000-000000000002"},
        )

        assert response.status_code == 409
        payload = response.json()
        assert payload["code"] == "invalid_status_transition"
    finally:
        get_settings.cache_clear()


def test_research_patch_rejects_status_id(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.patch(
            "/api/v1/research/00000000-0000-0000-0000-000000000001",
            json={"status_id": "00000000-0000-0000-0000-000000000002"},
        )

        assert response.status_code == 409
        payload = response.json()
        assert payload["code"] == "invalid_status_transition"
    finally:
        get_settings.cache_clear()


def test_test_patch_rejects_status_id(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.patch(
            "/api/v1/tests/00000000-0000-0000-0000-000000000001",
            json={"status_id": "00000000-0000-0000-0000-000000000002"},
        )

        assert response.status_code == 409
        payload = response.json()
        assert payload["code"] == "invalid_status_transition"
    finally:
        get_settings.cache_clear()


def test_tests_direct_creation_route_is_removed(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post(
            "/api/v1/tests",
            json={
                "research_id": "00000000-0000-0000-0000-000000000001",
                "indicator_id": "00000000-0000-0000-0000-000000000002",
            },
        )

        assert response.status_code == 405
    finally:
        get_settings.cache_clear()


def test_samples_direct_creation_route_is_removed(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post("/api/v1/samples", json={"name": "sample"})

        assert response.status_code == 405
    finally:
        get_settings.cache_clear()


def test_research_direct_creation_route_is_removed(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post(
            "/api/v1/research",
            json={
                "sample_id": "00000000-0000-0000-0000-000000000001",
                "research_goal_id": "00000000-0000-0000-0000-000000000002",
            },
        )

        assert response.status_code == 405
    finally:
        get_settings.cache_clear()


def test_direction_import_endpoint_accepts_type_form_field(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post(
            "/api/v1/directions/import",
            data={"type": "xlsx"},
            files={"file": ("directions.xlsx", b"payload", "application/octet-stream")},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["data"]["filename"] == "directions.xlsx"
        assert payload["data"]["type"] == "xlsx"
        assert payload["meta"]["operation"] == "directions.import"
    finally:
        get_settings.cache_clear()


def test_add_direction_sample_to_draft_direction_succeeds(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post(
            f"/api/v1/directions/{_DRAFT_DIRECTION_ID}/samples",
            json={"name": "Проба №1"},
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["data"]["direction_id"] == str(_DRAFT_DIRECTION_ID)
        assert payload["data"]["name"] == "Проба №1"
        assert payload["meta"]["operation"] == "samples.create"
    finally:
        get_settings.cache_clear()


def test_add_direction_sample_to_non_draft_direction_conflicts(
    monkeypatch: MonkeyPatch,
) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post(
            f"/api/v1/directions/{_REGISTERED_DIRECTION_ID}/samples",
            json={"name": "Проба №1"},
        )

        assert response.status_code == 409
        payload = response.json()
        assert payload["code"] == "direction_not_draft"
    finally:
        get_settings.cache_clear()


def test_add_direction_sample_to_missing_direction_not_found(
    monkeypatch: MonkeyPatch,
) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post(
            f"/api/v1/directions/{_MISSING_DIRECTION_ID}/samples",
            json={"name": "Проба №1"},
        )

        assert response.status_code == 404
    finally:
        get_settings.cache_clear()
