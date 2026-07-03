from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
import xlwt

from src.contexts.laboratory_workflow.application.legacy_direction_import import (
    LegacyDirectionXlsImportService,
)
from src.core.errors import ValidationError

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "legacy_direction.xls"


class RecordingDirection:
    def __init__(self, direction_id: str) -> None:
        self.id = UUID(direction_id)


class RecordingDirectionRepository:
    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []
        self.created_by_values: list[UUID | None] = []

    async def create(
        self, values: dict[str, Any], *, created_by: UUID | None = None
    ) -> RecordingDirection:
        self.created.append(values)
        self.created_by_values.append(created_by)
        return RecordingDirection("00000000-0000-0000-0000-000000000001")


class RecordingSample:
    def __init__(self, sample_id: str) -> None:
        self.id = UUID(sample_id)


class RecordingSampleRepository:
    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []
        self._next_id = 1

    async def create(self, values: dict[str, Any]) -> RecordingSample:
        self.created.append(values)
        sample_id = f"00000000-0000-0000-0000-{self._next_id:012d}"
        self._next_id += 1
        return RecordingSample(sample_id)


class RecordingResearchRepository:
    def __init__(self, goal_codes: dict[str, UUID] | None = None) -> None:
        self.created: list[dict[str, Any]] = []
        self._goal_codes = goal_codes or {}

    async def get_goal_id_by_code(self, code: str) -> UUID | None:
        return self._goal_codes.get(code)

    async def create(self, values: dict[str, Any]) -> object:
        self.created.append(values)
        return object()


def _write_row(sheet: xlwt.Worksheet, row: int, values: dict[int, Any]) -> None:
    for col, value in values.items():
        sheet.write(row, col, value)


def _minimal_xls_bytes(
    *,
    sample_rows: list[dict[int, Any]],
    document_number: str = "№ 000000123",
    sampling_date: str = "01.06.25",
    sampling_time: str = "09:00",
    signer_name: str | None = "Иванов И.И.",
    header_marker_row: int = 13,
) -> bytes:
    workbook = xlwt.Workbook()
    sheet = workbook.add_sheet("TDSheet")

    _write_row(sheet, 0, {2: "НАПРАВЛЕНИЕ"})
    _write_row(sheet, 1, {2: "проб пищевых продуктов на лабораторные исследования"})
    _write_row(sheet, 2, {2: document_number})
    _write_row(sheet, 3, {2: "ЦББ"})
    _write_row(sheet, 5, {2: "УПОО"})
    _write_row(sheet, 9, {2: sampling_time, 3: sampling_date, 6: sampling_time, 10: sampling_date})

    _write_row(
        sheet,
        header_marker_row,
        {0: "Дата выхода образца", 1: "Время выхода образца", 2: "№ п/п", 3: "Наименование"},
    )

    row_index = header_marker_row + 1
    for row_values in sample_rows:
        _write_row(sheet, row_index, row_values)
        row_index += 1

    footer_row = row_index + 1
    if signer_name is not None:
        _write_row(sheet, footer_row, {8: signer_name})

    buffer_path = "/tmp/_legacy_xls_fixture.xls"
    workbook.save(buffer_path)
    return Path(buffer_path).read_bytes()


async def test_parses_real_document_end_to_end() -> None:
    directions = RecordingDirectionRepository()
    samples = RecordingSampleRepository()
    research = RecordingResearchRepository(
        goal_codes={
            "BAK": UUID("00000000-0000-0000-0000-0000000000b1"),
            "TH": UUID("00000000-0000-0000-0000-0000000000b2"),
            "TB": UUID("00000000-0000-0000-0000-0000000000b3"),
            "RV": UUID("00000000-0000-0000-0000-0000000000b4"),
        }
    )
    service = LegacyDirectionXlsImportService(
        directions=directions, samples=samples, research=research
    )

    summary = await service.import_file("direction.xls", FIXTURE_PATH.read_bytes())

    assert summary.samples_processed == 94
    assert summary.samples_imported == 94
    assert summary.skipped_samples == 0
    assert summary.errors == []
    assert len(directions.created) == 1

    direction_values = directions.created[0]
    assert direction_values["year_no"] == 2025
    assert direction_values["base_no"] == 460
    assert direction_values["sampled_at"].strftime("%d.%m.%y %H:%M") == "27.05.25 11:57"
    assert direction_values["import_warnings"]["document"]["lab_department"] == "ЦББ"
    assert direction_values["import_warnings"]["document"]["sampling_department"] == "УПОО"
    assert direction_values["import_warnings"]["document"]["signer_name"] == "Куликов А.А."

    first_sample = samples.created[0]
    assert first_sample["name"] == "Грецкий орех 130 гр"
    assert first_sample["mass"] == "3 шт."
    assert first_sample["nomenclature_code"] == "00013560"
    assert first_sample["supplier"] == 'ООО "Компания "ГУД-ФУД"'

    assert summary.marks_created == len(research.created)
    assert summary.marks_created > 0

    # First sample has bak/th/tb/rv marked, pcr not marked -> 4 resolvable Research rows.
    first_sample_research = [
        r
        for r in research.created
        if r["sample_id"] == UUID("00000000-0000-0000-0000-000000000001")
    ]
    assert len(first_sample_research) == 4


async def test_rejects_non_xls_filename() -> None:
    service = LegacyDirectionXlsImportService(
        directions=RecordingDirectionRepository(),
        samples=RecordingSampleRepository(),
        research=RecordingResearchRepository(),
    )

    with pytest.raises(ValidationError):
        await service.import_file("direction.xlsx", b"not-xls")


async def test_rejects_oversized_file() -> None:
    service = LegacyDirectionXlsImportService(
        directions=RecordingDirectionRepository(),
        samples=RecordingSampleRepository(),
        research=RecordingResearchRepository(),
    )

    with pytest.raises(ValidationError):
        await service.import_file("direction.xls", b"0" * (5 * 1024 * 1024 + 1))


async def test_rejects_invalid_workbook_bytes() -> None:
    service = LegacyDirectionXlsImportService(
        directions=RecordingDirectionRepository(),
        samples=RecordingSampleRepository(),
        research=RecordingResearchRepository(),
    )

    with pytest.raises(ValidationError):
        await service.import_file("direction.xls", b"not-a-real-workbook")


async def test_requires_sampling_date() -> None:
    service = LegacyDirectionXlsImportService(
        directions=RecordingDirectionRepository(),
        samples=RecordingSampleRepository(),
        research=RecordingResearchRepository(),
    )
    content = _minimal_xls_bytes(sample_rows=[], sampling_date="", sampling_time="")

    with pytest.raises(ValidationError):
        await service.import_file("direction.xls", content)


async def test_skips_rows_missing_product_name() -> None:
    directions = RecordingDirectionRepository()
    samples = RecordingSampleRepository()
    service = LegacyDirectionXlsImportService(
        directions=directions, samples=samples, research=RecordingResearchRepository()
    )
    content = _minimal_xls_bytes(
        sample_rows=[
            {2: 1, 3: "Валидный образец", 6: "1", 7: "кг"},
            {2: 2, 6: "1", 7: "кг"},
        ]
    )

    summary = await service.import_file("direction.xls", content)

    assert summary.samples_processed == 2
    assert summary.samples_imported == 1
    assert summary.skipped_samples == 1
    assert len(summary.errors) == 1
    assert len(samples.created) == 1


async def test_warns_when_research_goal_code_is_unseeded() -> None:
    directions = RecordingDirectionRepository()
    samples = RecordingSampleRepository()
    research = RecordingResearchRepository(goal_codes={})
    service = LegacyDirectionXlsImportService(
        directions=directions, samples=samples, research=research
    )
    content = _minimal_xls_bytes(sample_rows=[{2: 1, 3: "Образец", 8: "х", 9: "х"}])

    summary = await service.import_file("direction.xls", content)

    assert summary.samples_imported == 1
    assert summary.marks_created == 0
    assert research.created == []
    assert len(summary.warnings) == 2
