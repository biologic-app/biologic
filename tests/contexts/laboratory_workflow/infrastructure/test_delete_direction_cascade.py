from datetime import UTC
from typing import Any, cast
from uuid import UUID

import pytest
from sqlalchemy import Update
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.laboratory_workflow.infrastructure.crud_repositories import (
    DirectionCrudRepository,
)
from src.core.errors import DomainConflictError, NotFoundError
from src.infrastructure.db.models import Direction

DIRECTION_ID = UUID("00000000-0000-0000-0000-000000000001")
DRAFT_STATUS_ID = UUID("00000000-0000-0000-0000-000000000002")
REGISTERED_STATUS_ID = UUID("00000000-0000-0000-0000-000000000003")
SAMPLE_ID = UUID("00000000-0000-0000-0000-000000000005")
RESEARCH_ID = UUID("00000000-0000-0000-0000-000000000007")


class _Result:
    def __init__(self, *, scalar: Any = None, scalars: list[Any] | None = None) -> None:
        self._scalar = scalar
        self._scalars = scalars or []

    def scalar_one_or_none(self) -> Any:
        return self._scalar

    def scalars(self) -> "_Result":
        return self

    def all(self) -> list[Any]:
        return self._scalars


class FakeAsyncSession:
    def __init__(
        self,
        *,
        direction: Direction | None,
        status_code: str | None = "draft",
        sample_ids: list[UUID] | None = None,
        research_ids: list[UUID] | None = None,
    ) -> None:
        self.direction = direction
        self.status_code = status_code
        self.sample_ids = sample_ids if sample_ids is not None else [SAMPLE_ID]
        self.research_ids = research_ids if research_ids is not None else [RESEARCH_ID]
        self.executed: list[Any] = []
        self.updates: list[Update] = []
        self.added: list[object] = []
        self.committed = False
        self._selects = 0

    async def execute(self, statement: Any) -> _Result:
        self.executed.append(statement)
        if isinstance(statement, Update):
            self.updates.append(statement)
            return _Result()
        self._selects += 1
        if self._selects == 1:  # read direction
            return _Result(scalar=self.direction)
        if self._selects == 2:  # status code
            return _Result(scalar=self.status_code)
        if self._selects == 3:  # sample ids
            return _Result(scalars=self.sample_ids)
        return _Result(scalars=self.research_ids)  # research ids

    def add(self, instance: object) -> None:
        self.added.append(instance)

    async def commit(self) -> None:
        self.committed = True


def _updated_tables(session: FakeAsyncSession) -> set[str]:
    tables: set[str] = set()
    for stmt in session.updates:
        compiled = str(
            stmt.compile(
                dialect=postgresql.dialect(),  # type: ignore[no-untyped-call]
                compile_kwargs={"literal_binds": True},
            )
        )
        tables.add(compiled.split()[1])  # UPDATE <table> ...
    return tables


@pytest.mark.asyncio
async def test_delete_draft_cascade_soft_deletes_children() -> None:
    direction = Direction(id=DIRECTION_ID, year_no=2026, status_id=DRAFT_STATUS_ID)
    fake_session = FakeAsyncSession(direction=direction, status_code="draft")
    repository = DirectionCrudRepository(session=cast(AsyncSession, fake_session))

    await repository.delete_draft_cascade(DIRECTION_ID)

    assert direction.deleted_at is not None
    assert direction.deleted_at.tzinfo is not None
    assert direction.deleted_at.utcoffset() == UTC.utcoffset(direction.deleted_at)
    assert fake_session.committed
    assert _updated_tables(fake_session) == {"tests", "research", "samples"}


@pytest.mark.asyncio
async def test_delete_draft_cascade_without_samples_only_deletes_direction() -> None:
    direction = Direction(id=DIRECTION_ID, year_no=2026, status_id=DRAFT_STATUS_ID)
    fake_session = FakeAsyncSession(
        direction=direction, status_code="draft", sample_ids=[], research_ids=[]
    )
    repository = DirectionCrudRepository(session=cast(AsyncSession, fake_session))

    await repository.delete_draft_cascade(DIRECTION_ID)

    assert direction.deleted_at is not None
    assert fake_session.committed
    assert fake_session.updates == []


@pytest.mark.asyncio
async def test_delete_draft_cascade_rejects_non_draft_direction() -> None:
    direction = Direction(id=DIRECTION_ID, year_no=2026, status_id=REGISTERED_STATUS_ID)
    fake_session = FakeAsyncSession(direction=direction, status_code="registered")
    repository = DirectionCrudRepository(session=cast(AsyncSession, fake_session))

    with pytest.raises(DomainConflictError) as exc:
        await repository.delete_draft_cascade(DIRECTION_ID)

    assert exc.value.extra["code"] == "direction_not_draft"
    assert "registered" in exc.value.detail
    assert direction.deleted_at is None
    assert not fake_session.committed
    assert fake_session.updates == []


@pytest.mark.asyncio
async def test_delete_draft_cascade_returns_not_found_for_missing_direction() -> None:
    fake_session = FakeAsyncSession(direction=None)
    repository = DirectionCrudRepository(session=cast(AsyncSession, fake_session))

    with pytest.raises(NotFoundError):
        await repository.delete_draft_cascade(DIRECTION_ID)

    assert not fake_session.committed
