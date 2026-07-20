from __future__ import annotations

from typing import Any, cast
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
        self.set_calls: list[tuple[UUID, list[UUID]]] = []

    async def list_labs_for_sample(self, sample_id: UUID) -> list[dict[str, Any]]:
        return self._labs

    async def set_labs_for_sample(
        self, sample_id: UUID, lab_ids: list[UUID]
    ) -> list[dict[str, Any]]:
        self.set_calls.append((sample_id, lab_ids))
        return [lab for lab in self._labs if lab["id"] in set(lab_ids)]

    async def suggest_research_goals(
        self, sample_id: UUID, sample_type_id: UUID
    ) -> list[dict[str, Any]]:
        self.suggest_calls.append((sample_id, sample_type_id))
        return self._goals


class FakeSubscriptionRepository:
    def __init__(self) -> None:
        self.rows: list[tuple[str, UUID, UUID]] = []

    def _items(self, entity_type: str, entity_id: UUID) -> list[dict[str, Any]]:
        return [
            {"user_id": user_id, "username": "user", "source": "manual"}
            for kind, eid, user_id in self.rows
            if kind == entity_type and eid == entity_id
        ]

    async def list_for_entity(
        self, entity_type: str, entity_id: UUID
    ) -> list[dict[str, Any]]:
        return self._items(entity_type, entity_id)

    async def subscribe(
        self, entity_type: str, entity_id: UUID, user_id: UUID
    ) -> list[dict[str, Any]]:
        key = (entity_type, entity_id, user_id)
        if key not in self.rows:
            self.rows.append(key)
        return self._items(entity_type, entity_id)

    async def unsubscribe(
        self, entity_type: str, entity_id: UUID, user_id: UUID
    ) -> list[dict[str, Any]]:
        self.rows = [row for row in self.rows if row != (entity_type, entity_id, user_id)]
        return self._items(entity_type, entity_id)


def _use_case(
    repo: FakeSampleLabRepository,
    subscriptions: FakeSubscriptionRepository | None = None,
) -> WorkflowCrudUseCase:
    return WorkflowCrudUseCase(
        directions=cast(Any, None),
        samples=cast(Any, None),
        research=cast(Any, None),
        tests=cast(Any, None),
        protocols=cast(Any, None),
        sample_labs=cast(Any, repo),
        subscriptions=cast(Any, subscriptions),
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


async def test_set_sample_labs_replaces_set_and_wraps_items() -> None:
    other_lab_id = UUID("00000000-0000-0000-0000-0000000000c2")
    repo = FakeSampleLabRepository(
        labs=[
            {"id": LAB_ID, "code": "BAK", "name": "Бактериологическая"},
            {"id": other_lab_id, "code": "RV", "name": "Радиационная"},
        ]
    )
    use_case = _use_case(repo)

    response = await use_case.set_sample_labs(SAMPLE_ID, [LAB_ID])

    assert repo.set_calls == [(SAMPLE_ID, [LAB_ID])]
    assert [item["code"] for item in response.items] == ["BAK"]
    assert response.meta.total == 1


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


async def test_subscribe_and_unsubscribe_round_trip() -> None:
    user_id = UUID("00000000-0000-0000-0000-0000000000e1")
    subs = FakeSubscriptionRepository()
    use_case = _use_case(FakeSampleLabRepository(), subs)

    subscribed = await use_case.subscribe("samples", SAMPLE_ID, user_id)
    assert [item["user_id"] for item in subscribed.items] == [str(user_id)]
    assert subscribed.meta.total == 1

    unsubscribed = await use_case.unsubscribe("samples", SAMPLE_ID, user_id)
    assert unsubscribed.items == []
    assert unsubscribed.meta.total == 0


def test_sample_lab_has_live_row_partial_unique_pair() -> None:
    indexes = {index.name: index for index in cast(Any, SampleLab.__table__).indexes}
    unique_pair = indexes["sample_labs_unique_pair"]

    assert unique_pair.unique is True
    assert [column.name for column in unique_pair.columns] == ["sample_id", "lab_id"]
    assert unique_pair.dialect_kwargs.get("postgresql_where") is not None
