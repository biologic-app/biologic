from src.contexts.laboratory_workflow.application.dto import (
    CommandResult,
    RegisterDirectionInput,
    RegisterSampleInput,
)
from src.contexts.laboratory_workflow.application.ports import WorkflowRepository


class WorkflowCommandService:
    def __init__(self, *, repository: WorkflowRepository) -> None:
        self.repository = repository

    async def register_direction(self, command: RegisterDirectionInput) -> CommandResult:
        return await self.repository.register_direction(
            direction_id=command.direction_id,
            actor_id=command.actor_id,
            comment=command.comment,
        )

    async def register_sample(self, command: RegisterSampleInput) -> CommandResult:
        return await self.repository.register_sample(
            sample_id=command.sample_id,
            actor_id=command.actor_id,
            received_at=command.received_at,
            deadline=command.deadline,
        )
