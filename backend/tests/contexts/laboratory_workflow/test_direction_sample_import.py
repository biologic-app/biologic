from __future__ import annotations

from io import BytesIO
from uuid import UUID

import pytest
from openpyxl import Workbook

from src.contexts.laboratory_workflow.application.direction_sample_import import (
    DirectionExcelImportService,
    DirectionJsonImportService,
)
from src.core.errors import ValidationError


class RecordingDirection:
    def __init__(self, direction_id: str) -> None:
        self.id = UUID(direction_id)


class RecordingDirectionRepository:
    def __init__(self, *, existing: set[tuple[int, int | None]] | None = None) -> None:
        self.created: list[dict[str, object]] = []
        self.created_by_values: list[UUID | None] = []
        self._next_id = 1
        self._existing = existing or set()

    async def create(
        self, values: dict[str, object], *, created_by: UUID | None = None
    ) -> RecordingDirection:
        self.created.append(values)
        self.created_by_values.append(created_by)
        direction_id = f"00000000-0000-0000-0000-{self._next_id:012d}"
        self._next_id += 1
        return RecordingDirection(direction_id)

    async def find_by_year_and_base_no(
        self, year_no: int, base_no: int | None, *, exclude_id: UUID | None = None
    ) -> object | None:
        return object() if (year_no, base_no) in self._existing else None


class RecordingSampleRepository:
    def __init__(self) -> None:
        self.created: list[dict[str, object]] = []

    async def create(
        self, values: dict[str, object], *, created_by: object | None = None
    ) -> object:
        self.created.append(values)
        return object()


def _xlsx_bytes(rows: list[list[object]], header: list[str]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(header)
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


async def test_excel_import_groups_rows_into_directions_with_samples() -> None:
    directions = RecordingDirectionRepository()
    samples = RecordingSampleRepository()
    service = DirectionExcelImportService(directions=directions, samples=samples)

    content = _xlsx_bytes(
        [
            [2026, 5001, "true", "Sample A", "1.2"],
            [2026, 5001, "false", "Sample B", "2.4"],
            [2026, 5002, "false", "Sample C", "0.5"],
        ],
        ["year_no", "base_no", "is_urgent", "sample_name", "mass"],
    )

    summary = await service.import_file("directions.xlsx", content)

    assert summary.rows_processed == 3
    assert summary.directions_created == 2
    assert summary.samples_created == 3
    assert summary.errors == []
    assert len(directions.created) == 2
    assert directions.created[0]["base_no"] == 5001
    assert directions.created[0]["is_urgent"] is True
    assert len(samples.created) == 3
    assert samples.created[0]["name"] == "Sample A"
    assert samples.created[0]["direction_id"] == UUID("00000000-0000-0000-0000-000000000001")
    assert samples.created[2]["direction_id"] == UUID("00000000-0000-0000-0000-000000000002")


async def test_excel_import_skips_direction_duplicating_existing_db_row() -> None:
    directions = RecordingDirectionRepository(existing={(2026, 5001)})
    samples = RecordingSampleRepository()
    service = DirectionExcelImportService(directions=directions, samples=samples)

    content = _xlsx_bytes(
        [
            [2026, 5001, "Duplicate Sample"],
            [2026, 5002, "New Sample"],
        ],
        ["year_no", "base_no", "sample_name"],
    )

    summary = await service.import_file("directions.xlsx", content)

    assert summary.rows_processed == 2
    assert summary.directions_created == 1
    assert summary.samples_created == 1
    assert summary.skipped_rows == 1
    assert len(summary.errors) == 1
    assert summary.errors[0]["row"] == 2
    assert len(directions.created) == 1
    assert directions.created[0]["base_no"] == 5002


async def test_excel_import_rejects_non_xlsx_filename() -> None:
    service = DirectionExcelImportService(
        directions=RecordingDirectionRepository(), samples=RecordingSampleRepository()
    )

    with pytest.raises(ValidationError):
        await service.import_file("directions.csv", b"not-excel")


async def test_excel_import_requires_year_no_column() -> None:
    service = DirectionExcelImportService(
        directions=RecordingDirectionRepository(), samples=RecordingSampleRepository()
    )
    content = _xlsx_bytes([["Sample A"]], ["sample_name"])

    with pytest.raises(ValidationError):
        await service.import_file("directions.xlsx", content)


async def test_excel_import_skips_rows_missing_required_fields() -> None:
    directions = RecordingDirectionRepository()
    samples = RecordingSampleRepository()
    service = DirectionExcelImportService(directions=directions, samples=samples)

    content = _xlsx_bytes(
        [
            [2026, 7001, "Valid Sample"],
            [None, 7002, "Missing year_no"],
            [2026, 7003, None],
        ],
        ["year_no", "base_no", "sample_name"],
    )

    summary = await service.import_file("directions.xlsx", content)

    assert summary.rows_processed == 3
    assert summary.directions_created == 1
    assert summary.samples_created == 1
    assert summary.skipped_rows == 2
    assert len(summary.errors) == 2


async def test_json_import_accepts_rows_wrapper_and_groups_directions() -> None:
    directions = RecordingDirectionRepository()
    samples = RecordingSampleRepository()
    service = DirectionJsonImportService(directions=directions, samples=samples)

    payload = (
        b'{"rows": ['
        b'{"year_no": 2026, "base_no": 6001, "sample_name": "JSON Sample A", "is_urgent": true},'
        b'{"year_no": 2026, "base_no": 6001, "sample_name": "JSON Sample B"},'
        b'{"year_no": 2026, "base_no": 6002, "sample_name": "JSON Sample C"}'
        b"]}"
    )

    summary = await service.import_file("directions.json", payload)

    assert summary.directions_created == 2
    assert summary.samples_created == 3
    assert directions.created[0]["is_urgent"] is True
    assert samples.created[1]["is_urgent"] is True  # inherited from direction


async def test_json_import_accepts_bare_array() -> None:
    directions = RecordingDirectionRepository()
    samples = RecordingSampleRepository()
    service = DirectionJsonImportService(directions=directions, samples=samples)

    payload = b'[{"year_no": 2026, "base_no": 8001, "sample_name": "Bare Array Sample"}]'

    summary = await service.import_file("directions.json", payload)

    assert summary.directions_created == 1
    assert summary.samples_created == 1


async def test_json_import_skips_direction_duplicating_existing_db_row() -> None:
    directions = RecordingDirectionRepository(existing={(2026, 6001)})
    samples = RecordingSampleRepository()
    service = DirectionJsonImportService(directions=directions, samples=samples)

    payload = (
        b'{"rows": ['
        b'{"year_no": 2026, "base_no": 6001, "sample_name": "Duplicate Sample"},'
        b'{"year_no": 2026, "base_no": 6002, "sample_name": "New Sample"}'
        b"]}"
    )

    summary = await service.import_file("directions.json", payload)

    assert summary.directions_created == 1
    assert summary.samples_created == 1
    assert summary.skipped_rows == 1
    assert len(summary.errors) == 1


async def test_json_import_rejects_non_json_filename() -> None:
    service = DirectionJsonImportService(
        directions=RecordingDirectionRepository(), samples=RecordingSampleRepository()
    )

    with pytest.raises(ValidationError):
        await service.import_file("directions.csv", b"[]")


async def test_json_import_rejects_invalid_json() -> None:
    service = DirectionJsonImportService(
        directions=RecordingDirectionRepository(), samples=RecordingSampleRepository()
    )

    with pytest.raises(ValidationError):
        await service.import_file("directions.json", b"{not-json")
