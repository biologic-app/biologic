from datetime import UTC, datetime
from uuid import UUID

import pytest
from fakes import WorkflowRepositoryFake

from src.contexts.laboratory_workflow.application.commands import WorkflowCommandService
from src.contexts.laboratory_workflow.application.dto import CommandResult, RegisterDirectionInput


class FakeWorkflowRepository(WorkflowRepositoryFake):
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
