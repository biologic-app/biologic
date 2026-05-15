from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.laboratory_workflow.application.dto import CommandResult
from src.core.errors import DomainConflictError


class SqlAlchemyWorkflowRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def register_direction(
        self,
        direction_id: UUID,
        actor_id: UUID,
        comment: str | None,
    ) -> CommandResult:
        raise DomainConflictError(
            code="invalid_status_transition",
            detail=(
                "Register direction persistence is not wired yet. "
                "Implement status lookup, draft validation, update, audit, and commit in Task 10."
            ),
        )

    async def register_sample(
        self,
        sample_id: UUID,
        actor_id: UUID,
        received_at: datetime,
        deadline: datetime | None,
    ) -> CommandResult:
        raise DomainConflictError(
            code="workflow_command_not_implemented",
            detail="Register sample persistence is not wired yet.",
        )

    async def reject_sample(
        self,
        sample_id: UUID,
        actor_id: UUID,
        reason: str,
    ) -> CommandResult:
        raise DomainConflictError(
            code="workflow_command_not_implemented",
            detail="Reject sample persistence is not wired yet.",
        )

    async def assign_research(
        self,
        sample_id: UUID,
        actor_id: UUID,
        research_goal_id: UUID,
        comment: str | None,
    ) -> CommandResult:
        raise DomainConflictError(
            code="workflow_command_not_implemented",
            detail="Assign research persistence is not wired yet.",
        )

    async def complete_test(
        self,
        test_id: UUID,
        actor_id: UUID,
        value: str,
        norm: str | None,
        comment: str | None,
    ) -> CommandResult:
        raise DomainConflictError(
            code="workflow_command_not_implemented",
            detail="Complete test persistence is not wired yet.",
        )
