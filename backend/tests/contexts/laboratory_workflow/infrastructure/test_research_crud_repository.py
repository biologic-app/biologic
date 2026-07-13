from typing import Any
from uuid import UUID

import pytest

from src.contexts.laboratory_workflow.infrastructure.crud_repositories import (
    ResearchCrudRepository,
)
from src.core.pagination import PaginationParams
from src.infrastructure.db.models import ChangeLog, Research

RESEARCH_ID = UUID("00000000-0000-0000-0000-000000000001")
SAMPLE_ID = UUID("00000000-0000-0000-0000-000000000002")
RESEARCH_GOAL_ID = UUID("00000000-0000-0000-0000-000000000003")
LAB_ID = UUID("00000000-0000-0000-0000-000000000004")
STATUS_ID = UUID("00000000-0000-0000-0000-000000000005")


class FakeResult:
    def __init__(
        self, *, scalar: int | None = None, scalars: list[Any] | None = None
    ) -> None:
        self.scalar = scalar
        self._scalars = scalars or []

    def scalar_one(self) -> int:
        if self.scalar is None:
            raise AssertionError("scalar_one was not configured")
        return self.scalar

    def scalars(self) -> "FakeResult":
        return self

    def all(self) -> list[Any]:
        return self._scalars


class FakeRowsResult:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self.rows = rows

    def all(self) -> list[tuple[Any, ...]]:
        return self.rows


class FakeReadResult:
    def __init__(self, row: Any) -> None:
        self.row = row

    def scalar_one_or_none(self) -> Any:
        return self.row


class FakeAsyncSession:
    def __init__(self, research: Research) -> None:
        self.research = research

    async def execute(self, statement: Any) -> FakeResult | FakeRowsResult:
        sql = str(statement)
        if "count" in sql:
            return FakeResult(scalar=1)
        if "FROM samples" in sql:
            return FakeRowsResult([(SAMPLE_ID, "Sample")])
        if "FROM research_goals" in sql:
            return FakeRowsResult([(RESEARCH_GOAL_ID, "goal", "Goal")])
        if "FROM labs" in sql:
            return FakeRowsResult([(LAB_ID, "lab", "Lab")])
        if "FROM research_statuses" in sql:
            return FakeRowsResult([(STATUS_ID, "draft", "Draft", "gray")])
        if "FROM research" in sql:
            return FakeRowsResult([(self.research, None)])
        raise AssertionError(f"Unexpected query: {sql}")


class FakeUpdateSession:
    def __init__(self, research: Research) -> None:
        self.research = research
        self.added: list[Any] = []
        self.committed = False
        self.refreshed: Any = None

    async def execute(self, statement: Any) -> FakeReadResult:
        sql = str(statement)
        if "FROM research" in sql:
            return FakeReadResult(self.research)
        raise AssertionError(f"Unexpected query: {sql}")

    def add(self, row: Any) -> None:
        self.added.append(row)

    async def commit(self) -> None:
        self.committed = True

    async def refresh(self, row: Any) -> None:
        self.refreshed = row


class FakeRelationSortSession:
    def __init__(self, research: Research) -> None:
        self.research = research
        self.statements: list[str] = []

    async def execute(self, statement: Any) -> FakeResult | FakeRowsResult:
        sql = str(statement)
        self.statements.append(sql)
        if "count" in sql:
            return FakeResult(scalar=1)
        if "FROM research_goals" in sql and "JOIN" not in sql:
            return FakeRowsResult([(RESEARCH_GOAL_ID, "goal", "Goal")])
        if "FROM research" in sql:
            return FakeRowsResult([(self.research, "Goal")])
        raise AssertionError(f"Unexpected query: {sql}")


@pytest.mark.asyncio
async def test_research_list_populates_requested_includes() -> None:
    research = Research(
        id=RESEARCH_ID,
        sample_id=SAMPLE_ID,
        research_goal_id=RESEARCH_GOAL_ID,
        lab_id=LAB_ID,
        status_id=STATUS_ID,
    )
    fake_session = FakeAsyncSession(research)
    repository = ResearchCrudRepository(session=fake_session)  # type: ignore[arg-type]

    page = await repository.list(
        PaginationParams(include="sample,research_goal,lab,status")
    )

    item = page.items[0]
    assert item.sample == {"id": SAMPLE_ID, "name": "Sample"}
    assert item.research_goal == {
        "id": RESEARCH_GOAL_ID,
        "code": "goal",
        "name": "Goal",
    }
    assert item.lab == {"id": LAB_ID, "code": "lab", "name": "Lab"}
    assert item.status == {"id": STATUS_ID, "code": "draft", "name": "Draft", "color": "gray"}


@pytest.mark.asyncio
async def test_research_list_sorts_by_research_goal_name() -> None:
    research = Research(
        id=RESEARCH_ID,
        sample_id=SAMPLE_ID,
        research_goal_id=RESEARCH_GOAL_ID,
        lab_id=LAB_ID,
        status_id=STATUS_ID,
    )
    fake_session = FakeRelationSortSession(research)
    repository = ResearchCrudRepository(session=fake_session)  # type: ignore[arg-type]

    page = await repository.list(
        PaginationParams(sort_by="research_goal.name", include="research_goal")
    )

    assert page.items == [research]
    assert any("JOIN research_goals" in statement for statement in fake_session.statements)


@pytest.mark.asyncio
async def test_research_update_writes_recommendation_audit_diff() -> None:
    research = Research(
        id=RESEARCH_ID,
        sample_id=SAMPLE_ID,
        research_goal_id=RESEARCH_GOAL_ID,
        lab_id=LAB_ID,
        status_id=STATUS_ID,
        recommendation="old recommendation",
    )
    fake_session = FakeUpdateSession(research)
    repository = ResearchCrudRepository(session=fake_session)  # type: ignore[arg-type]

    await repository.update(RESEARCH_ID, {"recommendation": "new recommendation"})

    audit_rows = [row for row in fake_session.added if isinstance(row, ChangeLog)]
    assert len(audit_rows) == 1
    audit = audit_rows[0]
    assert audit.entity_type == "research"
    assert audit.entity_id == RESEARCH_ID
    assert audit.action == "research.update"
    assert audit.diff == {
        "recommendation": {
            "from": "old recommendation",
            "to": "new recommendation",
        },
    }
    assert audit.snapshot == {"recommendation": "new recommendation"}
