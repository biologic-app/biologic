from src.contexts.laboratory_workflow.application.dto import (
    AssignResearchInput,
    CloseSampleInput,
    CommandResult,
    CompleteTestInput,
    CreateProtocolInput,
    IssueProtocolInput,
    RegisterDirectionInput,
    RegisterSampleInput,
    RejectSampleInput,
    ResearchCommandInput,
    TestCommandInput,
    UpdateProtocolInput,
)
from src.contexts.laboratory_workflow.application.ports import WorkflowRepository
from src.contexts.notifications.application.service import NotificationService


class WorkflowCommandService:
    def __init__(
        self,
        *,
        repository: WorkflowRepository,
        notification_service: NotificationService | None = None,
    ) -> None:
        self.repository = repository
        self.notification_service = notification_service

    async def register_direction(self, command: RegisterDirectionInput) -> CommandResult:
        result = await self.repository.register_direction(
            direction_id=command.direction_id,
            actor_id=command.actor_id,
            comment=command.comment,
        )
        await self._publish_repository_events()
        return result

    async def register_sample(self, command: RegisterSampleInput) -> CommandResult:
        result = await self.repository.register_sample(
            sample_id=command.sample_id,
            actor_id=command.actor_id,
            received_at=command.received_at,
            deadline=command.deadline,
        )
        await self._publish_repository_events()
        return result

    async def reject_sample(self, command: RejectSampleInput) -> CommandResult:
        result = await self.repository.reject_sample(
            sample_id=command.sample_id,
            actor_id=command.actor_id,
            reason=command.reason,
        )
        await self._publish_repository_events()
        return result

    async def assign_research(self, command: AssignResearchInput) -> CommandResult:
        return await self.repository.assign_research(
            sample_id=command.sample_id,
            actor_id=command.actor_id,
            research_goal_id=command.research_goal_id,
            comment=command.comment,
        )

    async def confirm_research(self, command: ResearchCommandInput) -> CommandResult:
        return await self.repository.confirm_research(
            research_id=command.research_id,
            actor_id=command.actor_id,
        )

    async def reject_research(self, command: ResearchCommandInput) -> CommandResult:
        result = await self.repository.reject_research(
            research_id=command.research_id,
            actor_id=command.actor_id,
            reason=command.reason or "",
        )
        await self._publish_repository_events()
        return result

    async def start_research(self, command: ResearchCommandInput) -> CommandResult:
        return await self.repository.start_research(
            research_id=command.research_id,
            actor_id=command.actor_id,
        )

    async def start_test(self, command: TestCommandInput) -> CommandResult:
        return await self.repository.start_test(test_id=command.test_id, actor_id=command.actor_id)

    async def complete_test(self, command: CompleteTestInput) -> CommandResult:
        return await self.repository.complete_test(
            test_id=command.test_id,
            actor_id=command.actor_id,
            value=command.value,
            norm=command.norm,
            comment=command.comment,
        )

    async def requeue_test(self, command: TestCommandInput) -> CommandResult:
        return await self.repository.requeue_test(
            test_id=command.test_id,
            actor_id=command.actor_id,
        )

    async def reject_test(self, command: TestCommandInput) -> CommandResult:
        return await self.repository.reject_test(
            test_id=command.test_id,
            actor_id=command.actor_id,
            reason=command.reason or "",
        )

    async def close_sample(self, command: CloseSampleInput) -> CommandResult:
        return await self.repository.close_sample(
            sample_id=command.sample_id,
            actor_id=command.actor_id,
            verdict=command.verdict,
            comment=command.comment,
        )

    async def create_protocol(self, command: CreateProtocolInput) -> CommandResult:
        return await self.repository.create_protocol(
            actor_id=command.actor_id,
            sample_ids=command.sample_ids,
            protocol_type_id=command.protocol_type_id,
            conclusion_id=command.conclusion_id,
            copies=command.copies,
        )

    async def update_protocol(self, command: UpdateProtocolInput) -> CommandResult:
        return await self.repository.update_protocol(
            protocol_id=command.protocol_id,
            actor_id=command.actor_id,
            protocol_type_id=command.protocol_type_id,
            conclusion_id=command.conclusion_id,
            copies=command.copies,
        )

    async def issue_protocol(self, command: IssueProtocolInput) -> CommandResult:
        return await self.repository.issue_protocol(
            protocol_id=command.protocol_id,
            actor_id=command.actor_id,
            issued_at=command.issued_at,
        )

    async def _publish_repository_events(self) -> None:
        if self.notification_service is None:
            return
        events = getattr(self.repository, "events", [])
        await self.notification_service.create_from_events(events)
