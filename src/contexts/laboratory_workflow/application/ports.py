from typing import Protocol
from uuid import UUID

from src.contexts.laboratory_workflow.application.dto import CommandResult


class WorkflowRepository(Protocol):
    async def register_direction(
        self,
        direction_id: UUID,
        actor_id: UUID,
        comment: str | None,
    ) -> CommandResult: ...

    async def register_sample(
        self,
        sample_id: UUID,
        actor_id: UUID,
        received_at: str,
        deadline: str | None,
    ) -> CommandResult: ...

    async def reject_sample(
        self,
        sample_id: UUID,
        actor_id: UUID,
        reason: str,
    ) -> CommandResult: ...

    async def assign_research(
        self,
        sample_id: UUID,
        actor_id: UUID,
        research_goal_id: UUID,
        comment: str | None,
    ) -> CommandResult: ...

    async def complete_test(
        self,
        test_id: UUID,
        actor_id: UUID,
        value: str,
        norm: str | None,
        comment: str | None,
    ) -> CommandResult: ...
