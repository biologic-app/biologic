"""Legacy institutional "НАПРАВЛЕНИЕ проб..." .xls form import.

The lab's sampling department exports a paper-form-styled .xls workbook:
a fixed header block (department names, sampling/delivery date-time,
document number, signer), a "one row per sample" table, and a signature
footer. This importer parses that specific layout and maps it onto a
single direction with nested samples — one file is one direction.

Header fields that have no matching direction column (department names,
signer name/position, document title) are kept verbatim under
``Direction.import_warnings`` for the registrar to reconcile by hand.
``sample_type_id`` is intentionally left unset since the workbook only
carries free-text names, not catalog ids. ``doctor_id``/``object_id`` are
best-effort auto-matched against the ``doctors``/``objects`` catalogs by
exact (case-insensitive, trimmed) name match — the signer name ("Фамилия
И.О.") against ``doctors.last_name`` + first-letter check on
``first_name``/``patronymic``, and the sampling department against
``objects.name``/``objects.full_name``. When no match or more than one
match is found, the field is left ``None`` and a warning is recorded so
the registrar still reconciles it by hand, as before.
The Бак/Т-Х/Т-Б/РВ/ПЦР mark columns are resolved against the
``research_goals`` catalog by code (``BAK``/``TH``/``TB``/``RV``/``PCR``);
a lab must seed those codes for marks to turn into ``Research`` rows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

import xlrd
from pydantic import BaseModel

from src.core.errors import ValidationError

MAX_IMPORT_BYTES = 5 * 1024 * 1024

_HEADER_MARKER = "№ п/п"

_MARK_COLUMNS: tuple[tuple[int, str], ...] = (
    (8, "BAK"),
    (9, "TH"),
    (10, "TB"),
    (11, "RV"),
    (12, "PCR"),
)

_TABLE_COLUMNS: dict[int, str] = {
    0: "release_date",
    1: "release_time",
    3: "product_name",
    6: "weight",
    7: "unit",
    13: "note",
    14: "section",
    15: "delivery_number",
    16: "nomenclature_code",
    17: "batch_code",
    18: "supplier",
}

_NAME_PATTERN = re.compile(r"[А-ЯЁ]\.\s?[А-ЯЁ]\.")


class LegacyDirectionImportSummary(BaseModel):
    filename: str
    direction_id: UUID | None
    samples_processed: int
    samples_imported: int
    skipped_samples: int
    marks_created: int
    errors: list[dict[str, object]]
    warnings: list[dict[str, object]]


def _issue(row: int | None, field_name: str, message: str) -> dict[str, object]:
    payload: dict[str, object] = {"field": field_name, "message": message}
    if row is not None:
        payload["row"] = row
    return payload


def _clean(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return value


def _to_bool_mark(value: Any) -> bool:
    cleaned = _clean(value)
    if cleaned is None:
        return False
    return str(cleaned).strip().lower() in ("х", "x", "+", "да", "yes")


def _get(rows: list[list[Any]], r: int, c: int) -> Any:
    if r < len(rows) and c < len(rows[r]):
        return rows[r][c]
    return None


def _cell_value(cell: Any, datemode: int) -> Any:
    if cell.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
        return None
    if cell.ctype == xlrd.XL_CELL_DATE:
        return xlrd.xldate_as_datetime(cell.value, datemode)
    return cell.value


def _load_rows(content: bytes) -> list[list[Any]]:
    try:
        book = xlrd.open_workbook(file_contents=content)
    except Exception as exc:  # noqa: BLE001 — any parse failure is a 422
        raise ValidationError(
            "Direction import file is not a valid .xls workbook.",
            extra={"errors": [_issue(None, "file", "Workbook could not be parsed.")]},
        ) from exc

    sheet = book.sheet_by_index(0)
    return [
        [_cell_value(sheet.cell(r, c), book.datemode) for c in range(sheet.ncols)]
        for r in range(sheet.nrows)
    ]


def _find_header_row(rows: list[list[Any]]) -> int:
    for i, row in enumerate(rows):
        if any(_HEADER_MARKER in str(v) for v in row if v not in (None, "")):
            return i
    raise ValidationError(
        "Direction import workbook has no sample table header.",
        extra={"errors": [_issue(None, "header", f"Marker '{_HEADER_MARKER}' not found.")]},
    )


def _find_footer_start(rows: list[list[Any]], header_row: int) -> int:
    for i in range(header_row + 1, len(rows)):
        if all(_clean(v) is None for v in rows[i]):
            return i
    return len(rows)


def _parse_ru_datetime(date_value: Any, time_value: Any) -> datetime | None:
    date_str = _clean(date_value)
    if date_str is None:
        return None
    time_str = _clean(time_value) or "00:00"
    try:
        parsed = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%y %H:%M")
    except ValueError:
        return None
    return parsed.replace(tzinfo=UTC)


@dataclass
class _ParsedHeader:
    document_number: str | None
    lab_department: str | None
    sampling_department: str | None
    sampled_at: datetime | None
    received_at: datetime | None


def _parse_header(rows: list[list[Any]]) -> _ParsedHeader:
    doc_number_raw = _clean(_get(rows, 2, 2))
    document_number = None
    if doc_number_raw:
        match = re.search(r"(\d+)", str(doc_number_raw))
        document_number = match.group(1) if match else str(doc_number_raw)

    return _ParsedHeader(
        document_number=document_number,
        lab_department=_clean(_get(rows, 3, 2)),
        sampling_department=_clean(_get(rows, 5, 2)),
        sampled_at=_parse_ru_datetime(_get(rows, 9, 3), _get(rows, 9, 2)),
        received_at=_parse_ru_datetime(_get(rows, 9, 10), _get(rows, 9, 6)),
    )


def _parse_footer(rows: list[list[Any]], footer_start: int) -> tuple[str | None, str | None]:
    signer_name: str | None = None
    signer_position: str | None = None
    for i in range(footer_start, len(rows)):
        for value in rows[i]:
            cleaned = _clean(value)
            if not cleaned or str(cleaned).startswith("("):
                continue
            if signer_name is None and _NAME_PATTERN.search(str(cleaned)):
                signer_name = str(cleaned)
            elif signer_position is None:
                signer_position = str(cleaned)
    return signer_name, signer_position


def _split_signer_name(signer_name: str) -> tuple[str, str, str] | None:
    """Split "Фамилия И.О." into (surname, first_initial, patronymic_initial)."""
    match = _NAME_PATTERN.search(signer_name)
    if match is None:
        return None
    letters = re.findall(r"[А-ЯЁ]", match.group(0))
    if len(letters) < 2:
        return None
    surname = signer_name[: match.start()].strip()
    if not surname:
        return None
    return surname, letters[0], letters[1]


async def _match_doctor(signer_name: str | None, doctors: Any) -> UUID | None:
    if doctors is None or not signer_name:
        return None
    split = _split_signer_name(signer_name)
    if split is None:
        return None
    surname, first_initial, patronymic_initial = split

    candidates = await doctors.find_by_last_name(surname)
    matches = [
        candidate
        for candidate in candidates
        if _initial_matches(candidate.first_name, first_initial)
        and _initial_matches(candidate.patronymic, patronymic_initial)
    ]
    if len(matches) == 1:
        return cast(UUID, matches[0].id)
    return None


def _initial_matches(name: str | None, initial: str) -> bool:
    if not name:
        return False
    return name.strip()[:1].upper() == initial.upper()


async def _match_object(sampling_department: str | None, objects: Any) -> UUID | None:
    if objects is None or not sampling_department:
        return None
    candidates = await objects.find_by_name(sampling_department)
    if len(candidates) == 1:
        return cast(UUID, candidates[0].id)
    return None


def _mass_text(weight: Any, unit: Any) -> str | None:
    weight = _clean(weight)
    unit = _clean(unit)
    parts = [str(part) for part in (weight, unit) if part is not None]
    return " ".join(parts) if parts else None


def _iter_table_rows(
    rows: list[list[Any]], header_row: int, footer_start: int
) -> list[tuple[int, dict[str, Any]]]:
    records: list[tuple[int, dict[str, Any]]] = []
    for i in range(header_row + 1, footer_start):
        row = rows[i]
        if all(_clean(v) is None for v in row):
            continue
        record: dict[str, Any] = {key: _get(rows, i, col) for col, key in _TABLE_COLUMNS.items()}
        record["marks"] = [code for col, code in _MARK_COLUMNS if _to_bool_mark(_get(rows, i, col))]
        records.append((i + 1, record))
    return records


class LegacyDirectionXlsImportService:
    """Imports one direction and its samples from a legacy institutional .xls form."""

    def __init__(
        self,
        *,
        directions: Any,
        samples: Any,
        research: Any,
        doctors: Any | None = None,
        objects: Any | None = None,
        created_by: UUID | None = None,
    ) -> None:
        self.directions = directions
        self.samples = samples
        self.research = research
        self.doctors = doctors
        self.objects = objects
        self.created_by = created_by

    async def import_file(self, filename: str, content: bytes) -> LegacyDirectionImportSummary:
        if not filename.lower().endswith(".xls"):
            raise ValidationError(
                "Only legacy .xls direction imports are supported.",
                extra={"errors": [_issue(None, "file", "Only .xls files are supported.")]},
            )
        if len(content) > MAX_IMPORT_BYTES:
            raise ValidationError(
                "Direction import file is too large.",
                extra={"errors": [_issue(None, "file", "File must not exceed 5 MB.")]},
            )

        rows = _load_rows(content)
        header = _parse_header(rows)
        header_row = _find_header_row(rows)
        footer_start = _find_footer_start(rows, header_row)
        signer_name, signer_position = _parse_footer(rows, footer_start)

        if header.sampled_at is None:
            raise ValidationError(
                "Direction import workbook is missing a valid sampling date.",
                extra={
                    "errors": [
                        _issue(
                            None,
                            "sampling_datetime",
                            "A parseable dd.mm.yy sampling date is required.",
                        )
                    ]
                },
            )

        warnings: list[dict[str, object]] = []
        direction_fields: dict[str, object] = {
            "year_no": header.sampled_at.year,
            "sampled_at": header.sampled_at,
        }
        if header.received_at is not None:
            direction_fields["received_at"] = header.received_at
        if header.document_number is not None:
            try:
                direction_fields["base_no"] = int(header.document_number)
            except ValueError:
                warnings.append(
                    _issue(
                        None,
                        "document_number",
                        "Could not parse as base_no; kept only in import_warnings.",
                    )
                )

        doctor_id = await _match_doctor(signer_name, self.doctors)
        object_id = await _match_object(header.sampling_department, self.objects)

        unresolved: list[str] = []
        if doctor_id is not None:
            direction_fields["doctor_id"] = doctor_id
        else:
            unresolved.append("doctor_id")
            warnings.append(
                _issue(
                    None,
                    "doctor_id",
                    "Could not auto-match a doctor from the signer name; reconcile manually.",
                )
            )
        if object_id is not None:
            direction_fields["object_id"] = object_id
        else:
            unresolved.append("object_id")
            warnings.append(
                _issue(
                    None,
                    "object_id",
                    "Could not auto-match an object from the sampling department; "
                    "reconcile manually.",
                )
            )

        direction_fields["import_warnings"] = {
            "source": "legacy_xls",
            "unresolved": unresolved,
            "document": {
                "document_number": header.document_number,
                "lab_department": header.lab_department,
                "sampling_department": header.sampling_department,
                "signer_name": signer_name,
                "signer_position": signer_position,
            },
        }

        errors: list[dict[str, object]] = []

        existing = await self.directions.find_by_year_and_base_no(
            direction_fields["year_no"], direction_fields.get("base_no")
        )
        if existing is not None:
            errors.append(
                {
                    "row": None,
                    "errors": [
                        _issue(
                            None,
                            "year_no",
                            "Направление с таким годом и номером уже существует, "
                            "пропущено.",
                        )
                    ],
                }
            )
            return LegacyDirectionImportSummary(
                filename=filename,
                direction_id=None,
                samples_processed=0,
                samples_imported=0,
                skipped_samples=0,
                marks_created=0,
                errors=errors,
                warnings=warnings,
            )

        direction_row = await self.directions.create(direction_fields, created_by=self.created_by)

        samples_processed = 0
        samples_imported = 0
        skipped_samples = 0
        marks_created = 0

        for row_number, record in _iter_table_rows(rows, header_row, footer_start):
            samples_processed += 1
            product_name = _clean(record.get("product_name"))
            if not product_name:
                skipped_samples += 1
                errors.append(
                    {
                        "row": row_number,
                        "errors": [_issue(None, "product_name", "Value is required.")],
                    }
                )
                continue

            sample_values: dict[str, object] = {
                "direction_id": direction_row.id,
                "name": product_name,
            }
            mass = _mass_text(record.get("weight"), record.get("unit"))
            if mass is not None:
                sample_values["mass"] = mass
            for source, target in (
                ("note", "comment"),
                ("section", "section"),
                ("delivery_number", "delivery"),
                ("nomenclature_code", "nomenclature_code"),
                ("batch_code", "batch_code"),
                ("supplier", "supplier"),
            ):
                value = _clean(record.get(source))
                if value is not None:
                    sample_values[target] = value

            deadline = _parse_ru_datetime(record.get("release_date"), record.get("release_time"))
            if deadline is not None:
                sample_values["deadline"] = deadline

            sample_row = await self.samples.create(sample_values)
            samples_imported += 1

            for code in record["marks"]:
                goal_id = await self.research.get_goal_id_by_code(code)
                if goal_id is None:
                    warnings.append(
                        _issue(
                            row_number,
                            code,
                            f"research_goals catalog has no code '{code}'; mark skipped.",
                        )
                    )
                    continue
                await self.research.create(
                    {"sample_id": sample_row.id, "research_goal_id": goal_id}
                )
                marks_created += 1

        return LegacyDirectionImportSummary(
            filename=filename,
            direction_id=direction_row.id,
            samples_processed=samples_processed,
            samples_imported=samples_imported,
            skipped_samples=skipped_samples,
            marks_created=marks_created,
            errors=errors,
            warnings=warnings,
        )
