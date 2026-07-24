from datetime import datetime
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
        received_at: datetime,
        deadline: datetime | None,
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
        verdict: bool | None,
        workflow_run_id: UUID | None = None,
    ) -> CommandResult: ...

    async def reject_research(
        self,
        research_id: UUID,
        actor_id: UUID,
        reason: str,
    ) -> CommandResult: ...

    async def reject_test(
        self,
        test_id: UUID,
        actor_id: UUID,
        reason: str,
        workflow_run_id: UUID | None = None,
    ) -> CommandResult: ...

    async def close_sample(
        self,
        sample_id: UUID,
        actor_id: UUID,
        verdict: str,
        comment: str | None,
    ) -> CommandResult: ...

    async def create_protocol(
        self,
        actor_id: UUID,
        sample_ids: list[UUID],
        protocol_type_id: UUID | None,
        conclusion_id: UUID | None,
        copies: int | None,
    ) -> CommandResult: ...

    async def update_protocol(
        self,
        protocol_id: UUID,
        actor_id: UUID,
        protocol_type_id: UUID | None,
        conclusion_id: UUID | None,
        copies: int | None,
    ) -> CommandResult: ...

    async def issue_protocol(
        self,
        protocol_id: UUID,
        actor_id: UUID,
        issued_at: datetime | None,
    ) -> CommandResult: ...

    async def resolve_notification_targets(
        self, entity_type: str, entity_id: UUID
    ) -> set[UUID]: ...
