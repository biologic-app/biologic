from __future__ import annotations

from typing import Any
from uuid import UUID

from src.contexts.laboratory_workflow.application.crud import WorkflowCrudUseCase
from src.infrastructure.db.models import SampleLab

SAMPLE_ID = UUID("00000000-0000-0000-0000-0000000000a1")
SAMPLE_TYPE_ID = UUID("00000000-0000-0000-0000-0000000000b1")
LAB_ID = UUID("00000000-0000-0000-0000-0000000000c1")
GOAL_ID = UUID("00000000-0000-0000-0000-0000000000d1")


class FakeSampleLabRepository:
    def __init__(
        self,
        *,
        labs: list[dict[str, Any]] | None = None,
        goals: list[dict[str, Any]] | None = None,
    ) -> None:
        self._labs = labs or []
        self._goals = goals or []
        self.suggest_calls: list[tuple[UUID, UUID]] = []

    async def list_labs_for_sample(self, sample_id: UUID) -> list[dict[str, Any]]:
        return self._labs

    async def suggest_research_goals(
        self, sample_id: UUID, sample_type_id: UUID
    ) -> list[dict[str, Any]]:
        self.suggest_calls.append((sample_id, sample_type_id))
        return self._goals


def _use_case(repo: FakeSampleLabRepository) -> WorkflowCrudUseCase:
    return WorkflowCrudUseCase(
        directions=None,
        samples=None,
        research=None,
        tests=None,
        protocols=None,
        sample_labs=repo,
    )


async def test_list_sample_labs_wraps_items_and_meta() -> None:
    repo = FakeSampleLabRepository(
        labs=[{"id": LAB_ID, "code": "BAK", "name": "Бактериологическая"}]
    )
    use_case = _use_case(repo)

    response = await use_case.list_sample_labs(SAMPLE_ID)

    assert [item["code"] for item in response.items] == ["BAK"]
    assert response.items[0]["name"] == "Бактериологическая"
    assert response.items[0]["id"] == str(LAB_ID)
    assert response.meta.total == 1
    assert response.meta.has_more is False


async def test_suggest_research_goals_wraps_items_and_meta() -> None:
    repo = FakeSampleLabRepository(
        goals=[
            {
                "id": GOAL_ID,
                "code": "RG-BAK-01",
                "name": "Общее микробное число (КМАФАнМ)",
                "comment": None,
                "lab_id": LAB_ID,
                "lab_name": "Бактериологическая",
            }
        ]
    )
    use_case = _use_case(repo)

    response = await use_case.suggest_research_goals(SAMPLE_ID, SAMPLE_TYPE_ID)

    assert repo.suggest_calls == [(SAMPLE_ID, SAMPLE_TYPE_ID)]
    assert response.items[0]["code"] == "RG-BAK-01"
    assert response.items[0]["lab_id"] == str(LAB_ID)
    assert response.items[0]["lab_name"] == "Бактериологическая"
    assert response.meta.total == 1


def test_sample_lab_has_live_row_partial_unique_pair() -> None:
    indexes = {index.name: index for index in SampleLab.__table__.indexes}
    unique_pair = indexes["sample_labs_unique_pair"]

    assert unique_pair.unique is True
    assert [column.name for column in unique_pair.columns] == ["sample_id", "lab_id"]
    assert unique_pair.dialect_kwargs.get("postgresql_where") is not None
