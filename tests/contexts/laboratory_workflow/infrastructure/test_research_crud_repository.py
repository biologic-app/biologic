from typing import Any
from uuid import UUID

import pytest

from src.contexts.laboratory_workflow.infrastructure.crud_repositories import (
    ResearchCrudRepository,
)
from src.core.pagination import PaginationParams
from src.infrastructure.db.models import Research

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
            return FakeRowsResult([(STATUS_ID, "draft", "Draft")])
        if "FROM research" in sql:
            return FakeResult(scalars=[self.research])
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
    assert item.status == {"id": STATUS_ID, "code": "draft", "name": "Draft"}
