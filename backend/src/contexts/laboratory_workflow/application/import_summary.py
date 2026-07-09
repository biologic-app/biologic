"""Unified summary shape for `POST /directions/import`, regardless of source format.

Excel/JSON imports (`direction_sample_import.py`) and the legacy .xls import
(`legacy_direction_import.py`) each return their own summary DTO, shaped after
their own row/record model. `WorkflowImportSummary` normalizes both into one
response contract so API consumers only ever handle a single shape.
"""

from __future__ import annotations

from pydantic import BaseModel

from src.contexts.laboratory_workflow.application.direction_sample_import import (
    WorkflowImportSummary as DirectionSampleImportSummary,
)
from src.contexts.laboratory_workflow.application.legacy_direction_import import (
    LegacyDirectionImportSummary,
)


class WorkflowImportSummary(BaseModel):
    filename: str
    directions_created: int
    samples_created: int
    research_created: int = 0
    skipped: int
    errors: list[dict[str, object]]
    warnings: list[dict[str, object]]


def from_direction_sample_summary(
    summary: DirectionSampleImportSummary,
) -> WorkflowImportSummary:
    return WorkflowImportSummary(
        filename=summary.filename,
        directions_created=summary.directions_created,
        samples_created=summary.samples_created,
        research_created=0,
        skipped=summary.skipped_rows,
        errors=summary.errors,
        warnings=summary.warnings,
    )


def from_legacy_summary(summary: LegacyDirectionImportSummary) -> WorkflowImportSummary:
    return WorkflowImportSummary(
        filename=summary.filename,
        directions_created=1 if summary.direction_id is not None else 0,
        samples_created=summary.samples_imported,
        research_created=summary.marks_created,
        skipped=summary.skipped_samples,
        errors=summary.errors,
        warnings=summary.warnings,
    )
