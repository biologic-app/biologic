from typing import Any, cast
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.laboratory_workflow.infrastructure.crud_repositories import (
    DirectionCrudRepository,
)
from src.core.errors import DomainConflictError
from src.infrastructure.db.models import Direction

DIRECTION_ID = UUID("00000000-0000-0000-0000-000000000001")
OTHER_DIRECTION_ID = UUID("00000000-0000-0000-0000-000000000002")
DRAFT_STATUS_ID = UUID("00000000-0000-0000-0000-000000000009")


class _Result:
    def __init__(self, *, scalar: Any = None) -> None:
        self._scalar = scalar

    def scalar_one_or_none(self) -> Any:
        return self._scalar

    def scalars(self) -> "_Result":
        return self

    def first(self) -> Any:
        return self._scalar

    def all(self) -> list[Any]:
        return [] if self._scalar is None else [self._scalar]


class FakeAsyncSession:
    """Executes a scripted sequence of `select` results, in call order.

    Mirrors the fake session pattern used in
    tests/contexts/laboratory_workflow/infrastructure/test_delete_direction_cascade.py.
    """

    def __init__(
        self,
        *,
        select_results: list[_Result],
        commit_error: Exception | None = None,
    ) -> None:
        self._select_results = list(select_results)
        self._commit_error = commit_error
        self.executed: list[Any] = []
        self.added: list[object] = []
        self.committed = False
        self.rolled_back = False
        self.commit_calls = 0

    async def execute(self, statement: Any) -> _Result:
        self.executed.append(statement)
        return self._select_results.pop(0)

    def add(self, instance: object) -> None:
        self.added.append(instance)

    async def commit(self) -> None:
        self.commit_calls += 1
        if self._commit_error is not None:
            error, self._commit_error = self._commit_error, None
            raise error
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def refresh(self, instance: object) -> None:
        return None


@pytest.mark.asyncio
async def test_create_raises_conflict_when_year_base_no_pair_already_exists() -> None:
    existing = Direction(id=OTHER_DIRECTION_ID, year_no=2026, base_no=17)
    session = FakeAsyncSession(
        select_results=[
            _Result(scalar=DRAFT_STATUS_ID),  # default status lookup
            _Result(scalar=existing),  # find_by_year_and_base_no
        ]
    )
    repository = DirectionCrudRepository(session=cast(AsyncSession, session))

    with pytest.raises(DomainConflictError) as exc:
        await repository.create({"year_no": 2026, "base_no": 17})

    assert exc.value.extra["code"] == "direction_duplicate"
    assert exc.value.detail == "Направление с таким годом и номером уже существует."
    assert not session.committed
    assert session.added == []


@pytest.mark.asyncio
async def test_create_succeeds_when_year_base_no_pair_is_free() -> None:
    session = FakeAsyncSession(
        select_results=[
            _Result(scalar=DRAFT_STATUS_ID),  # default status lookup
            _Result(scalar=None),  # find_by_year_and_base_no -> no duplicate
        ]
    )
    repository = DirectionCrudRepository(session=cast(AsyncSession, session))

    row = await repository.create({"year_no": 2026, "base_no": 18})

    assert row.year_no == 2026
    assert row.base_no == 18
    assert session.committed
    assert len(session.added) == 1


@pytest.mark.asyncio
async def test_create_converts_integrity_error_race_into_domain_conflict() -> None:
    session = FakeAsyncSession(
        select_results=[
            _Result(scalar=DRAFT_STATUS_ID),
            _Result(scalar=None),  # pre-check found nothing (race with a concurrent insert)
        ],
        commit_error=IntegrityError("INSERT", {}, Exception("duplicate key")),
    )
    repository = DirectionCrudRepository(session=cast(AsyncSession, session))

    with pytest.raises(DomainConflictError) as exc:
        await repository.create({"year_no": 2026, "base_no": 19})

    assert exc.value.extra["code"] == "direction_duplicate"
    assert session.rolled_back
    assert not session.committed


@pytest.mark.asyncio
async def test_update_raises_conflict_when_new_pair_belongs_to_another_direction() -> None:
    current = Direction(id=DIRECTION_ID, year_no=2026, base_no=20)
    other = Direction(id=OTHER_DIRECTION_ID, year_no=2026, base_no=21)
    session = FakeAsyncSession(
        select_results=[
            _Result(scalar=current),  # self.read(direction_id)
            _Result(scalar=other),  # find_by_year_and_base_no excluding self
        ]
    )
    repository = DirectionCrudRepository(session=cast(AsyncSession, session))

    with pytest.raises(DomainConflictError) as exc:
        await repository.update(DIRECTION_ID, {"base_no": 21})

    assert exc.value.extra["code"] == "direction_duplicate"
    assert not session.committed


@pytest.mark.asyncio
async def test_update_keeping_own_year_base_no_is_not_treated_as_duplicate() -> None:
    current = Direction(id=DIRECTION_ID, year_no=2026, base_no=20)
    session = FakeAsyncSession(
        select_results=[
            _Result(scalar=current),  # self.read(direction_id)
            _Result(scalar=None),  # find_by_year_and_base_no excludes self -> no match
        ]
    )
    repository = DirectionCrudRepository(session=cast(AsyncSession, session))

    row = await repository.update(DIRECTION_ID, {"base_no": 20})

    assert row.base_no == 20
    assert session.committed
