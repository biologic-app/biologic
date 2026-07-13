"""Read-only XLSX rendering for protocol documents and rejected-sample excerpts.

The data is fetched by :class:`ProtocolReportRepository` (infrastructure) and
handed here as plain dataclasses; this module only turns it into an ``.xlsx``
byte stream via ``openpyxl`` — no database or framework dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from uuid import UUID

from openpyxl import Workbook

_DOCUMENT_TITLE = "Протокол испытаний"
_EXCERPT_TITLE = "Выписка из протокола — бракованные образцы"
_SHEET_TITLE = "Протокол"
_BASE_COLUMNS = (
    "Название образца",
    "Тип образца",
    "Статус",
    "Направление",
    "Дата поступления",
)
_REASON_COLUMN = "Причина брака"


@dataclass(frozen=True)
class ProtocolSampleRow:
    name: str
    sample_type: str | None
    status: str | None
    direction_no: str | None
    received_at: datetime | None
    reject_reason: str | None = None


@dataclass(frozen=True)
class ProtocolDocumentData:
    protocol_id: UUID
    year_no: int
    formed_at: datetime
    protocol_type: str | None
    conclusion: str | None
    copies: int | None
    rows: tuple[ProtocolSampleRow, ...]


def _short_id(protocol_id: UUID) -> str:
    return protocol_id.hex[:8]


def _protocol_number(data: ProtocolDocumentData) -> str:
    return f"{data.year_no}-{_short_id(data.protocol_id)}"


def protocol_document_filename(data: ProtocolDocumentData) -> str:
    return f"protocol_{_protocol_number(data)}.xlsx"


def protocol_excerpt_filename(data: ProtocolDocumentData) -> str:
    return f"protocol_{_protocol_number(data)}_excerpt.xlsx"


def _format_dt(value: datetime | None) -> str:
    return value.isoformat() if value is not None else ""


def render_protocol_document(
    data: ProtocolDocumentData,
    *,
    title: str,
    include_reason: bool,
) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = _SHEET_TITLE

    worksheet.append([title])
    worksheet.append(["Протокол №", _protocol_number(data)])
    worksheet.append(["Дата формирования", _format_dt(data.formed_at)])
    worksheet.append(["Тип протокола", data.protocol_type or ""])
    worksheet.append(["Заключение", data.conclusion or ""])
    worksheet.append(["Количество копий", "" if data.copies is None else data.copies])
    worksheet.append([])

    columns = [*_BASE_COLUMNS, _REASON_COLUMN] if include_reason else list(_BASE_COLUMNS)
    worksheet.append(columns)
    for row in data.rows:
        values = [
            row.name,
            row.sample_type or "",
            row.status or "",
            row.direction_no or "",
            _format_dt(row.received_at),
        ]
        if include_reason:
            values.append(row.reject_reason or "")
        worksheet.append(values)

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def render_full_document(data: ProtocolDocumentData) -> bytes:
    return render_protocol_document(data, title=_DOCUMENT_TITLE, include_reason=False)


def render_excerpt(data: ProtocolDocumentData) -> bytes:
    return render_protocol_document(data, title=_EXCERPT_TITLE, include_reason=True)
