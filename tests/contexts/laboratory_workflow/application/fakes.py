from datetime import datetime
from uuid import UUID

from src.contexts.laboratory_workflow.application.dto import CommandResult
from src.contexts.laboratory_workflow.application.ports import WorkflowRepository


class WorkflowRepositoryFake(WorkflowRepository):
    async def register_direction(
        self,
        direction_id: UUID,
        actor_id: UUID,
        comment: str | None,
    ) -> CommandResult:
        raise AssertionError("register_direction should not be called")

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

    async def confirm_research(self, research_id: UUID, actor_id: UUID) -> CommandResult:
        raise AssertionError("confirm_research should not be called")

    async def start_research(self, research_id: UUID, actor_id: UUID) -> CommandResult:
        raise AssertionError("start_research should not be called")

    async def start_test(self, test_id: UUID, actor_id: UUID) -> CommandResult:
        raise AssertionError("start_test should not be called")

    async def requeue_test(self, test_id: UUID, actor_id: UUID) -> CommandResult:
        raise AssertionError("requeue_test should not be called")

    async def reject_test(
        self,
        test_id: UUID,
        actor_id: UUID,
        reason: str,
    ) -> CommandResult:
        raise AssertionError("reject_test should not be called")

    async def close_sample(
        self,
        sample_id: UUID,
        actor_id: UUID,
        verdict: str,
        comment: str | None,
    ) -> CommandResult:
        raise AssertionError("close_sample should not be called")

    async def create_protocol(
        self,
        actor_id: UUID,
        sample_ids: list[UUID],
        protocol_type_id: UUID | None,
        conclusion_id: UUID | None,
        copies: int | None,
    ) -> CommandResult:
        raise AssertionError("create_protocol should not be called")

    async def update_protocol(
        self,
        protocol_id: UUID,
        actor_id: UUID,
        protocol_type_id: UUID | None,
        conclusion_id: UUID | None,
        copies: int | None,
    ) -> CommandResult:
        raise AssertionError("update_protocol should not be called")

    async def issue_protocol(
        self,
        protocol_id: UUID,
        actor_id: UUID,
        issued_at: datetime | None,
    ) -> CommandResult:
        raise AssertionError("issue_protocol should not be called")
