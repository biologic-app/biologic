from datetime import UTC, datetime
from uuid import UUID

import pytest

from src.contexts.laboratory_workflow.application.commands import WorkflowCommandService
from src.contexts.laboratory_workflow.application.dto import CommandResult, RegisterDirectionInput
from src.contexts.laboratory_workflow.application.ports import WorkflowRepository


class FakeWorkflowRepository(WorkflowRepository):
    def __init__(self) -> None:
        self.called_with: tuple[UUID, UUID, str | None] | None = None

    async def register_direction(
        self,
        direction_id: UUID,
        actor_id: UUID,
        comment: str | None,
    ) -> CommandResult:
        self.called_with = (direction_id, actor_id, comment)
        return CommandResult(
            id=direction_id,
            status_id=UUID("00000000-0000-0000-0000-000000000002"),
            updated_at=datetime(2026, 5, 14, 10, 0, tzinfo=UTC),
        )

    async def register_sample(
        self,
        sample_id: UUID,
        actor_id: UUID,
        received_at: datetime,
        deadline: datetime | None,
    ) -> CommandResult:
        raise AssertionError("register_sample should not be called")

    async def reject_sample(
        self,
        sample_id: UUID,
        actor_id: UUID,
        reason: str,
    ) -> CommandResult:
        raise AssertionError("reject_sample should not be called")

    async def assign_research(
        self,
        sample_id: UUID,
        actor_id: UUID,
        research_goal_id: UUID,
        comment: str | None,
    ) -> CommandResult:
        raise AssertionError("assign_research should not be called")

    async def complete_test(
        self,
        test_id: UUID,
        actor_id: UUID,
        value: str,
        norm: str | None,
        comment: str | None,
    ) -> CommandResult:
        raise AssertionError("complete_test should not be called")


@pytest.mark.asyncio
async def test_register_direction_delegates_to_repository() -> None:
    repository = FakeWorkflowRepository()
    service = WorkflowCommandService(repository=repository)
    direction_id = UUID("00000000-0000-0000-0000-000000000001")
    actor_id = UUID("00000000-0000-0000-0000-000000000003")

    result = await service.register_direction(
        RegisterDirectionInput(
            direction_id=direction_id,
            actor_id=actor_id,
            comment="Ready for laboratory workflow",
        ),
    )

    assert result.id == direction_id
    assert repository.called_with == (direction_id, actor_id, "Ready for laboratory workflow")
