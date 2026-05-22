from datetime import UTC, datetime
from uuid import UUID

import pytest
from fakes import WorkflowRepositoryFake

from src.contexts.laboratory_workflow.application.commands import WorkflowCommandService
from src.contexts.laboratory_workflow.application.dto import CommandResult, RegisterSampleInput


class FakeWorkflowRepository(WorkflowRepositoryFake):
    def __init__(self) -> None:
        self.called_with: tuple[UUID, UUID, datetime, datetime | None] | None = None

    async def register_sample(
        self,
        sample_id: UUID,
        actor_id: UUID,
        received_at: datetime,
        deadline: datetime | None,
    ) -> CommandResult:
        self.called_with = (sample_id, actor_id, received_at, deadline)
        return CommandResult(
            id=sample_id,
            status_id=UUID("00000000-0000-0000-0000-000000000002"),
            updated_at=datetime(2026, 5, 14, 10, 0, tzinfo=UTC),
        )


@pytest.mark.asyncio
async def test_register_sample_delegates_to_repository() -> None:
    repository = FakeWorkflowRepository()
    service = WorkflowCommandService(repository=repository)
    sample_id = UUID("00000000-0000-0000-0000-000000000001")
    actor_id = UUID("00000000-0000-0000-0000-000000000003")
    received_at = datetime(2026, 5, 14, 10, 0, tzinfo=UTC)
    deadline = datetime(2026, 5, 16, 10, 0, tzinfo=UTC)

    result = await service.register_sample(
        RegisterSampleInput(
            sample_id=sample_id,
            actor_id=actor_id,
            received_at=received_at,
            deadline=deadline,
        ),
    )

    assert result.id == sample_id
    assert repository.called_with == (sample_id, actor_id, received_at, deadline)
