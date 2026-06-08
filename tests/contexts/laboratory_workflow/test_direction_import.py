from __future__ import annotations

from datetime import datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from pytest import MonkeyPatch

from src.app_factory import create_app
from src.contexts.laboratory_workflow.application.imports import DirectionImportService
from src.contexts.laboratory_workflow.presentation.router import get_workflow_crud_use_case
from src.core.config import get_settings
from src.core.pagination import PageMeta, PaginationParams
from src.core.responses import ListResponse, ResponseMeta, SingleResponse


class RecordingDirectionRepository:
    def __init__(self) -> None:
        self.created: list[dict[str, object]] = []

    async def create(self, values: dict[str, object]) -> object:
        self.created.append(values)
        return object()


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

    async def import_directions(
        self, filename: str, content: bytes
    ) -> SingleResponse[dict[str, object]]:
        return SingleResponse(
            data={
                "filename": filename,
                "processed": 1,
                "imported": 1,
                "skipped": 0,
                "errors": [],
                "warnings": [],
            },
            meta=ResponseMeta(operation="directions.import"),
        )

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
    app.dependency_overrides[get_workflow_crud_use_case] = lambda: FakeWorkflowCrudUseCase()
    return TestClient(app)


@pytest.mark.parametrize("filename", ["directions.csv", "directions.CSV"])
async def test_direction_import_service_imports_valid_csv(filename: str) -> None:
    repository = RecordingDirectionRepository()
    service = DirectionImportService(directions=repository)

    result = await service.import_file(
        filename,
        b"year_no,base_no,is_urgent,doctor_id,sampled_at\n"
        b"2026,17,true,00000000-0000-0000-0000-000000000001,2026-06-08T10:00:00Z\n",
    )

    assert result.imported == 1
    assert result.errors == []
    assert repository.created == [
        {
            "year_no": 2026,
            "base_no": 17,
            "is_urgent": True,
            "doctor_id": UUID("00000000-0000-0000-0000-000000000001"),
            "sampled_at": datetime.fromisoformat("2026-06-08T10:00:00+00:00"),
        },
    ]


async def test_direction_import_service_skips_invalid_rows() -> None:
    repository = RecordingDirectionRepository()
    service = DirectionImportService(directions=repository)

    result = await service.import_file(
        "directions.csv",
        b"year_no,base_no\n,abc\n2026,18\n",
    )

    assert result.processed == 2
    assert result.imported == 1
    assert result.skipped == 1
    assert result.errors[0]["row"] == 2
    assert repository.created == [{"year_no": 2026, "base_no": 18}]


def test_direction_import_endpoint_accepts_multipart(monkeypatch: MonkeyPatch) -> None:
    try:
        client = _client(monkeypatch)

        response = client.post(
            "/api/v1/directions/import",
            files={"file": ("directions.csv", b"year_no\n2026\n", "text/csv")},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["data"]["filename"] == "directions.csv"
        assert payload["data"]["imported"] == 1
        assert payload["meta"]["operation"] == "directions.import"
    finally:
        get_settings.cache_clear()
