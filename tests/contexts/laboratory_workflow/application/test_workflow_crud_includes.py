from types import SimpleNamespace
from uuid import UUID

import pytest

from src.contexts.laboratory_workflow.application.crud import WorkflowCrudUseCase
from src.contexts.laboratory_workflow.infrastructure.crud_repositories import (
    RepositoryPage,
)
from src.core.pagination import PaginationParams


class FakeResearchRepository:
    async def list(self, params: PaginationParams) -> RepositoryPage:
        return RepositoryPage(
            items=[
                SimpleNamespace(
                    id=UUID("00000000-0000-0000-0000-000000000001"),
                    sample_id=UUID("00000000-0000-0000-0000-000000000002"),
                    research_goal_id=UUID("00000000-0000-0000-0000-000000000003"),
                    lab_id=UUID("00000000-0000-0000-0000-000000000004"),
                    status_id=UUID("00000000-0000-0000-0000-000000000005"),
                    comment=None,
                    recommendation=None,
                    received_at=None,
                    completed_at=None,
                    created_at=None,
                    updated_at=None,
                    sample={
                        "id": UUID("00000000-0000-0000-0000-000000000002"),
                        "name": "Sample",
                    },
                    research_goal={
                        "id": UUID("00000000-0000-0000-0000-000000000003"),
                        "code": "goal",
                        "name": "Goal",
                    },
                    lab={
                        "id": UUID("00000000-0000-0000-0000-000000000004"),
                        "code": "lab",
                        "name": "Lab",
                    },
                    status={
                        "id": UUID("00000000-0000-0000-0000-000000000005"),
                        "code": "draft",
                        "name": "Draft",
                    },
                ),
            ],
            total=1,
            has_more=False,
            next_cursor=None,
        )


@pytest.mark.asyncio
async def test_research_list_serializes_requested_includes() -> None:
    use_case = WorkflowCrudUseCase(
        directions=object(),  # type: ignore[arg-type]
        samples=object(),  # type: ignore[arg-type]
        research=FakeResearchRepository(),  # type: ignore[arg-type]
        tests=object(),  # type: ignore[arg-type]
        protocols=object(),  # type: ignore[arg-type]
    )

    response = await use_case.list_research(
        PaginationParams(include="sample,research_goal,lab,status"),
    )

    item = response.items[0]
    assert item["sample"] == {
        "id": "00000000-0000-0000-0000-000000000002",
        "name": "Sample",
    }
    assert item["research_goal"] == {
        "id": "00000000-0000-0000-0000-000000000003",
        "code": "goal",
        "name": "Goal",
    }
    assert item["lab"] == {
        "id": "00000000-0000-0000-0000-000000000004",
        "code": "lab",
        "name": "Lab",
    }
    assert item["status"] == {
        "id": "00000000-0000-0000-0000-000000000005",
        "code": "draft",
        "name": "Draft",
    }
    assert response.meta.includes_applied == [
        "sample",
        "research_goal",
        "lab",
        "status",
    ]
