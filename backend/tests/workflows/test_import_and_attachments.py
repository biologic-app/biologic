from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest
from wf_fakes import FakeWorkflowsRepo, FakeWorkflowsUoW, uow_factory

from src.application.workflows.dto import (
    ImportEventInput,
    ImportRunInput,
    ImportTemplateInput,
    ImportVersionInput,
)
from src.application.workflows.use_cases.attachments import WorkflowAttachmentUseCase
from src.application.workflows.use_cases.import_templates import WorkflowImportUseCase
from src.core.errors import BadRequestError, ValidationError

RUN_ID = UUID("00000000-0000-0000-0000-0000000000c1")


def _valid_schema() -> dict[str, Any]:
    return {
        "formatVersion": 2,
        "title": "T",
        "nodes": [
            {"id": "n1", "type": "start", "data": {"label": "Start"}},
            {"id": "n2", "type": "end", "data": {"label": "End"}},
        ],
        "edges": [{"id": "e1", "source": "n1", "target": "n2"}],
    }


@pytest.mark.asyncio
async def test_import_lays_out_templates_versions_runs_and_events() -> None:
    templates = [
        ImportTemplateInput(
            title="Imported",
            current_version=1,
            versions=[ImportVersionInput(version=1, schema=_valid_schema())],
            runs=[
                ImportRunInput(
                    schema_version=1,
                    title="Run 1",
                    status="completed",
                    events=[
                        ImportEventInput(kind="comment", payload={"text": "hi"}, author="a"),
                        ImportEventInput(kind="activity", payload={"note": "started"}),
                    ],
                )
            ],
        )
    ]
    workflows = FakeWorkflowsRepo()
    uow = FakeWorkflowsUoW(workflows)
    use_case = WorkflowImportUseCase(uow_factory=uow_factory(uow))

    response = await use_case.import_bundle(templates)

    assert response.data == {"templates": 1, "versions": 1, "runs": 1, "events": 2}
    assert len(workflows.created_templates) == 1
    assert len(workflows.created_versions) == 1
    assert len(workflows.created_runs) == 1
    assert len(workflows.events) == 2
    assert uow.committed is True


@pytest.mark.asyncio
async def test_import_rejects_invalid_schema_before_writing() -> None:
    bad = _valid_schema()
    bad["formatVersion"] = 1
    templates = [
        ImportTemplateInput(
            title="Bad",
            versions=[ImportVersionInput(version=1, schema=bad)],
        )
    ]
    workflows = FakeWorkflowsRepo()
    uow = FakeWorkflowsUoW(workflows)
    use_case = WorkflowImportUseCase(uow_factory=uow_factory(uow))

    with pytest.raises(ValidationError):
        await use_case.import_bundle(templates)

    assert workflows.created_templates == []
    assert uow.committed is False


@pytest.mark.asyncio
async def test_attachment_over_limit_is_rejected() -> None:
    workflows = FakeWorkflowsRepo()
    uow = FakeWorkflowsUoW(workflows)
    use_case = WorkflowAttachmentUseCase(uow_factory=uow_factory(uow), max_mb=1)

    oversized = b"x" * (1 * 1024 * 1024 + 1)
    with pytest.raises(BadRequestError):
        await use_case.create(RUN_ID, "photo", "big.bin", "application/octet-stream", oversized)

    assert workflows.attachments == []
    assert uow.committed is False


@pytest.mark.asyncio
async def test_attachment_within_limit_is_stored() -> None:
    workflows = FakeWorkflowsRepo()
    uow = FakeWorkflowsUoW(workflows)
    use_case = WorkflowAttachmentUseCase(uow_factory=uow_factory(uow), max_mb=10)

    response = await use_case.create(RUN_ID, "photo", "ok.txt", "text/plain", b"hello")

    assert response.data["size_bytes"] == 5
    assert response.data["filename"] == "ok.txt"
    assert response.data["storage"] == "db"
    assert "data" not in response.data
    assert uow.committed is True
