from src.contexts.laboratory_workflow.application.dto import (
    CommandResult,
    RegisterDirectionInput,
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
