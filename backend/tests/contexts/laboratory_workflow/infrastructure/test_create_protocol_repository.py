from typing import Any, cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.laboratory_workflow.infrastructure.repositories import (
    SqlAlchemyWorkflowRepository,
)
from src.core.errors import DomainConflictError
from src.infrastructure.db.models import Protocol, Sample

COMPLETED_STATUS_ID = UUID("00000000-0000-0000-0000-000000000301")
REJECTED_STATUS_ID = UUID("00000000-0000-0000-0000-000000000302")
PENDING_STATUS_ID = UUID("00000000-0000-0000-0000-000000000303")
SAMPLE_ID = UUID("00000000-0000-0000-0000-000000000304")
ACTOR_ID = UUID("00000000-0000-0000-0000-000000000305")


class _ScalarResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value


class _SamplesResult:
    def __init__(self, samples: list[Sample]) -> None:
        self._samples = samples

    def scalars(self) -> "_SamplesResult":
        return self

    def all(self) -> list[Sample]:
        return list(self._samples)


class FakeAsyncSession:
    """Answers the three queries create_protocol issues: completed id, rejected
    id, then the samples select — in that order."""

    def __init__(self, samples: list[Sample]) -> None:
        self._results: list[object] = [
            _ScalarResult(COMPLETED_STATUS_ID),
            _ScalarResult(REJECTED_STATUS_ID),
            _SamplesResult(samples),
        ]
        self._index = 0
        self.added: list[object] = []
        self.flushed = False

    async def execute(self, statement: Any) -> object:
        result = self._results[self._index]
        self._index += 1
        return result

    def add(self, instance: object) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        self.flushed = True


@pytest.mark.asyncio
async def test_create_protocol_accepts_rejected_samples() -> None:
    sample = Sample(id=SAMPLE_ID, name="Проба", status_id=REJECTED_STATUS_ID)
    session = FakeAsyncSession(samples=[sample])
    repository = SqlAlchemyWorkflowRepository(session=cast(AsyncSession, session))

    result = await repository.create_protocol(
        actor_id=ACTOR_ID,
        sample_ids=[SAMPLE_ID],
        protocol_type_id=None,
        conclusion_id=None,
        copies=1,
    )

    assert sample.protocol_id == result.id
    assert session.flushed
    assert any(isinstance(item, Protocol) for item in session.added)


@pytest.mark.asyncio
async def test_create_protocol_accepts_completed_samples() -> None:
    sample = Sample(id=SAMPLE_ID, name="Проба", status_id=COMPLETED_STATUS_ID)
    session = FakeAsyncSession(samples=[sample])
    repository = SqlAlchemyWorkflowRepository(session=cast(AsyncSession, session))

    result = await repository.create_protocol(
        actor_id=ACTOR_ID,
        sample_ids=[SAMPLE_ID],
        protocol_type_id=None,
        conclusion_id=None,
        copies=1,
    )

    assert sample.protocol_id == result.id
    assert session.flushed


@pytest.mark.asyncio
async def test_create_protocol_rejects_non_terminal_samples() -> None:
    sample = Sample(id=SAMPLE_ID, name="Проба", status_id=PENDING_STATUS_ID)
    session = FakeAsyncSession(samples=[sample])
    repository = SqlAlchemyWorkflowRepository(session=cast(AsyncSession, session))

    with pytest.raises(DomainConflictError) as exc:
        await repository.create_protocol(
            actor_id=ACTOR_ID,
            sample_ids=[SAMPLE_ID],
            protocol_type_id=None,
            conclusion_id=None,
            copies=1,
        )

    assert exc.value.extra["code"] == "protocol_not_issuable"
    assert not session.flushed
