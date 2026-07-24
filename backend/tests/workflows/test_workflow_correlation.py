from __future__ import annotations

from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from wf_fakes import RecordingSession

from src.contexts.laboratory_workflow.infrastructure.repositories import (
    SqlAlchemyWorkflowRepository,
)
from src.infrastructure.db.models import ChangeLog, WorkflowRunEvent
from src.infrastructure.repositories.workflows import SqlAlchemyWorkflowsRepository

RUN_ID = UUID("00000000-0000-0000-0000-0000000000b1")
OTHER_RUN_ID = UUID("00000000-0000-0000-0000-0000000000b2")
ENTITY_ID = UUID("00000000-0000-0000-0000-0000000000b3")
ACTOR_ID = UUID("00000000-0000-0000-0000-0000000000b4")


def _repo() -> tuple[SqlAlchemyWorkflowRepository, RecordingSession]:
    session = RecordingSession()
    repo = SqlAlchemyWorkflowRepository(session=cast(AsyncSession, session))
    return repo, session


def test_add_audit_stamps_active_workflow_run_id() -> None:
    repo, session = _repo()
    repo._workflow_run_id = RUN_ID
    repo._add_audit(
        entity_type="tests",
        entity_id=ENTITY_ID,
        action="test_completed",
        actor_id=ACTOR_ID,
        diff={},
    )
    entry = next(item for item in session.added if isinstance(item, ChangeLog))
    assert entry.workflow_run_id == RUN_ID


def test_add_audit_defaults_to_none_without_run() -> None:
    repo, session = _repo()
    repo._add_audit(
        entity_type="tests",
        entity_id=ENTITY_ID,
        action="test_completed",
        actor_id=ACTOR_ID,
        diff={},
    )
    entry = next(item for item in session.added if isinstance(item, ChangeLog))
    assert entry.workflow_run_id is None


def test_add_audit_explicit_kwarg_wins() -> None:
    repo, session = _repo()
    repo._workflow_run_id = RUN_ID
    repo._add_audit(
        entity_type="tests",
        entity_id=ENTITY_ID,
        action="test_completed",
        actor_id=ACTOR_ID,
        diff={},
        workflow_run_id=OTHER_RUN_ID,
    )
    entry = next(item for item in session.added if isinstance(item, ChangeLog))
    assert entry.workflow_run_id == OTHER_RUN_ID


@pytest.mark.asyncio
async def test_append_event_is_append_only() -> None:
    session = RecordingSession()
    repo = SqlAlchemyWorkflowsRepository(session=cast(AsyncSession, session))

    await repo.append_event(RUN_ID, "comment", None, {"text": "first"}, "alice")
    await repo.append_event(RUN_ID, "comment", None, {"text": "second"}, "bob")

    events = [row for row in session.added if isinstance(row, WorkflowRunEvent)]
    # Two concurrent appends create two distinct rows — no lost update.
    assert len(events) == 2
    assert [e.payload["text"] for e in events] == ["first", "second"]
