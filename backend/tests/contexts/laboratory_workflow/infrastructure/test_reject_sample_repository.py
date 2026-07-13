from datetime import UTC
from typing import Any, cast
from uuid import UUID

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from src.contexts.laboratory_workflow.infrastructure.repositories import (
    SqlAlchemyWorkflowRepository,
)
from src.core.errors import DomainConflictError, NotFoundError
from src.infrastructure.db.models import ChangeLog, Sample

SAMPLE_ID = UUID("00000000-0000-0000-0000-000000000201")
PENDING_STATUS_ID = UUID("00000000-0000-0000-0000-000000000202")
REJECTED_STATUS_ID = UUID("00000000-0000-0000-0000-000000000203")
ACTOR_ID = UUID("00000000-0000-0000-0000-000000000204")


class RowResult:
    def __init__(self, row: Sample | None) -> None:
        self.row = row

    def scalar_one_or_none(self) -> Sample | None:
        return self.row


class ScalarResult:
    def __init__(self, value: UUID | str | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> UUID | str | None:
        return self.value


class FakeAsyncSession:
    def __init__(
        self,
        *,
        sample: Sample | None,
        current_status_code: str | None = "pending",
        target_status_id: UUID | None = REJECTED_STATUS_ID,
    ) -> None:
        self.sample = sample
        self.current_status_code = current_status_code
        self.target_status_id = target_status_id
        self.statements: list[Select[tuple[Any, ...]]] = []
        self.added: list[object] = []
        self.flushed = False

    async def execute(
        self,
        statement: Select[tuple[Any, ...]],
    ) -> RowResult | ScalarResult:
        self.statements.append(statement)
        if len(self.statements) == 1:
            return RowResult(self.sample)
        if len(self.statements) == 2:
            return ScalarResult(self.current_status_code)
        return ScalarResult(self.target_status_id)

    def add(self, instance: object) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        self.flushed = True


@pytest.mark.asyncio
async def test_reject_sample_changes_registered_to_rejected_and_writes_audit() -> None:
    sample = Sample(id=SAMPLE_ID, name="Sample", status_id=PENDING_STATUS_ID)
    fake_session = FakeAsyncSession(sample=sample, current_status_code="registered")
    repository = SqlAlchemyWorkflowRepository(session=cast(AsyncSession, fake_session))

    result = await repository.reject_sample(
        sample_id=SAMPLE_ID,
        actor_id=ACTOR_ID,
        reason="Container damaged",
    )

    assert result.id == SAMPLE_ID
    assert result.status_id == REJECTED_STATUS_ID
    assert result.updated_at.tzinfo is not None
    assert result.updated_at.utcoffset() == UTC.utcoffset(result.updated_at)
    assert sample.status_id == REJECTED_STATUS_ID
    assert sample.updated_by == ACTOR_ID
    assert fake_session.flushed

    audit_entry = next(item for item in fake_session.added if isinstance(item, ChangeLog))
    assert audit_entry.entity_type == "samples"
    assert audit_entry.entity_id == SAMPLE_ID
    assert audit_entry.action == "sample_rejected"
    assert audit_entry.actor_id == ACTOR_ID
    assert audit_entry.snapshot == {"status_code": "rejected", "reason": "Container damaged"}
    assert audit_entry.diff == {
        "status_code": {"from": "registered", "to": "rejected"},
        "reason": "Container damaged",
    }
    assert len(repository.events) == 1
    assert repository.events[0].event_type == "SampleRejected"
    assert repository.events[0].from_code == "registered"
    assert repository.events[0].to_code == "rejected"
    assert repository.events[0].reason == "Container damaged"


@pytest.mark.asyncio
async def test_reject_sample_rejects_pending_status() -> None:
    # Образец нельзя забраковать сразу с регистрации (pending → rejected запрещён).
    sample = Sample(id=SAMPLE_ID, name="Sample", status_id=PENDING_STATUS_ID)
    fake_session = FakeAsyncSession(sample=sample, current_status_code="pending")
    repository = SqlAlchemyWorkflowRepository(session=cast(AsyncSession, fake_session))

    with pytest.raises(DomainConflictError) as exc:
        await repository.reject_sample(
            sample_id=SAMPLE_ID,
            actor_id=ACTOR_ID,
            reason="Container damaged",
        )

    assert exc.value.extra["code"] == "invalid_status_transition"
    assert sample.status_id == PENDING_STATUS_ID
    assert not fake_session.flushed


@pytest.mark.asyncio
async def test_reject_sample_rejects_invalid_initial_status() -> None:
    sample = Sample(id=SAMPLE_ID, name="Sample", status_id=REJECTED_STATUS_ID)
    fake_session = FakeAsyncSession(sample=sample, current_status_code="completed")
    repository = SqlAlchemyWorkflowRepository(session=cast(AsyncSession, fake_session))

    with pytest.raises(DomainConflictError) as exc:
        await repository.reject_sample(
            sample_id=SAMPLE_ID,
            actor_id=ACTOR_ID,
            reason="Container damaged",
        )

    assert exc.value.extra["code"] == "invalid_status_transition"
    assert sample.status_id == REJECTED_STATUS_ID
    assert not fake_session.flushed


@pytest.mark.asyncio
async def test_reject_sample_returns_not_found_for_missing_sample() -> None:
    fake_session = FakeAsyncSession(sample=None)
    repository = SqlAlchemyWorkflowRepository(session=cast(AsyncSession, fake_session))

    with pytest.raises(NotFoundError):
        await repository.reject_sample(
            sample_id=SAMPLE_ID,
            actor_id=ACTOR_ID,
            reason="Container damaged",
        )

    assert not fake_session.flushed


@pytest.mark.asyncio
async def test_reject_sample_status_lookup_uses_stable_code() -> None:
    sample = Sample(id=SAMPLE_ID, name="Sample", status_id=PENDING_STATUS_ID)
    fake_session = FakeAsyncSession(sample=sample, current_status_code="registered")
    repository = SqlAlchemyWorkflowRepository(session=cast(AsyncSession, fake_session))

    await repository.reject_sample(
        sample_id=SAMPLE_ID,
        actor_id=ACTOR_ID,
        reason="Container damaged",
    )

    compiled_lookup = str(
        fake_session.statements[2].compile(
            dialect=postgresql.dialect(),  # type: ignore[no-untyped-call]
            compile_kwargs={"literal_binds": True},
        ),
    )
    assert "sample_statuses.code = 'rejected'" in compiled_lookup
    assert "sample_statuses.name" not in compiled_lookup
