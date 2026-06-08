from __future__ import annotations

import csv
from collections.abc import Callable
from datetime import datetime
from io import StringIO
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from src.core.errors import ValidationError

MAX_IMPORT_BYTES = 5 * 1024 * 1024


class DirectionImportSummary(BaseModel):
    filename: str
    processed: int
    imported: int
    skipped: int
    errors: list[dict[str, object]]
    warnings: list[dict[str, object]]


class DirectionImportService:
    def __init__(self, *, directions: Any) -> None:
        self.directions = directions

    async def import_file(self, filename: str, content: bytes) -> DirectionImportSummary:
        if not filename.lower().endswith(".csv"):
            raise ValidationError(
                "Only CSV direction imports are supported.",
                extra={"errors": [_issue(None, "file", "Only .csv files are supported.")]},
            )

        if len(content) > MAX_IMPORT_BYTES:
            raise ValidationError(
                "Direction import file is too large.",
                extra={"errors": [_issue(None, "file", "File must not exceed 5 MB.")]},
            )

        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValidationError(
                "Direction import file must be UTF-8 encoded.",
                extra={"errors": [_issue(None, "file", "File must be UTF-8 encoded.")]},
            ) from exc

        reader = csv.DictReader(StringIO(text))
        if not reader.fieldnames:
            raise ValidationError(
                "Direction import CSV has no header row.",
                extra={"errors": [_issue(1, "header", "CSV header row is required.")]},
            )

        fieldnames = [field.strip() for field in reader.fieldnames if field]
        if "year_no" not in fieldnames:
            raise ValidationError(
                "Direction import CSV must contain year_no.",
                extra={"errors": [_issue(1, "year_no", "year_no column is required.")]},
            )

        unknown_fields = sorted(set(fieldnames) - set(_FIELD_PARSERS))
        warnings = [_issue(None, field, "Column is ignored.") for field in unknown_fields]
        processed = 0
        imported = 0
        errors: list[dict[str, object]] = []

        for row_number, row in enumerate(reader, start=2):
            processed += 1
            values, row_errors = _parse_row(row)
            if row_errors:
                errors.append({"row": row_number, "errors": row_errors})
                continue

            await self.directions.create(values)
            imported += 1

        return DirectionImportSummary(
            filename=filename,
            processed=processed,
            imported=imported,
            skipped=processed - imported,
            errors=errors,
            warnings=warnings,
        )


def _issue(row: int | None, field: str, message: str) -> dict[str, object]:
    payload: dict[str, object] = {"field": field, "message": message}
    if row is not None:
        payload["row"] = row
    return payload


def _parse_int(value: str) -> int:
    return int(value)


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "да"}:
        return True
    if normalized in {"0", "false", "no", "n", "нет"}:
        return False
    raise ValueError("Invalid boolean value.")


def _parse_uuid(value: str) -> UUID:
    return UUID(value)


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


_FIELD_PARSERS: dict[str, Callable[[str], object]] = {
    "year_no": _parse_int,
    "base_no": _parse_int,
    "is_done": _parse_bool,
    "is_urgent": _parse_bool,
    "doctor_id": _parse_uuid,
    "object_id": _parse_uuid,
    "sampled_at": _parse_datetime,
    "received_at": _parse_datetime,
    "completed_at": _parse_datetime,
}


def _parse_row(row: dict[str, str | None]) -> tuple[dict[str, object], list[dict[str, object]]]:
    values: dict[str, object] = {}
    errors: list[dict[str, object]] = []

    for field, parser in _FIELD_PARSERS.items():
        raw = row.get(field)
        if raw is None or raw.strip() == "":
            if field == "year_no":
                errors.append(_issue(None, field, "Value is required."))
            continue

        try:
            values[field] = parser(raw.strip())
        except (TypeError, ValueError):
            errors.append(_issue(None, field, "Value has invalid format."))

    return values, errors
