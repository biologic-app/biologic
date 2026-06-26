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
from src.contexts.notifications.application.service import NotificationService
from src.domain.uow import UnitOfWork, UnitOfWorkFactory


class WorkflowCommandService:
    """Lifecycle command service driven by the single Unit of Work.

    Every command opens one UoW: the workflow mutation, the notifications it
    emits and the audit history rows all commit atomically on one session.
    """

    def __init__(self, *, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def register_direction(self, command: RegisterDirectionInput) -> CommandResult:
        async with self._uow_factory() as uow:
            result = await uow.workflow.register_direction(
                direction_id=command.direction_id,
                actor_id=command.actor_id,
                comment=command.comment,
            )
            await self._publish_events(uow)
            await uow.commit()
            return result

    async def register_sample(self, command: RegisterSampleInput) -> CommandResult:
        async with self._uow_factory() as uow:
            result = await uow.workflow.register_sample(
                sample_id=command.sample_id,
                actor_id=command.actor_id,
                received_at=command.received_at,
                deadline=command.deadline,
            )
            await self._publish_events(uow)
            await uow.commit()
            return result

    async def reject_sample(self, command: RejectSampleInput) -> CommandResult:
        async with self._uow_factory() as uow:
            result = await uow.workflow.reject_sample(
                sample_id=command.sample_id,
                actor_id=command.actor_id,
                reason=command.reason,
            )
            await self._publish_events(uow)
            await uow.commit()
            return result

    async def assign_research(self, command: AssignResearchInput) -> CommandResult:
        async with self._uow_factory() as uow:
            result = await uow.workflow.assign_research(
                sample_id=command.sample_id,
                actor_id=command.actor_id,
                research_goal_id=command.research_goal_id,
                comment=command.comment,
            )
            await uow.commit()
            return result

    async def confirm_research(self, command: ResearchCommandInput) -> CommandResult:
        async with self._uow_factory() as uow:
            result = await uow.workflow.confirm_research(
                research_id=command.research_id,
                actor_id=command.actor_id,
            )
            await uow.commit()
            return result

    async def reject_research(self, command: ResearchCommandInput) -> CommandResult:
        async with self._uow_factory() as uow:
            result = await uow.workflow.reject_research(
                research_id=command.research_id,
                actor_id=command.actor_id,
                reason=command.reason or "",
            )
            await self._publish_events(uow)
            await uow.commit()
            return result

    async def start_research(self, command: ResearchCommandInput) -> CommandResult:
        async with self._uow_factory() as uow:
            result = await uow.workflow.start_research(
                research_id=command.research_id,
                actor_id=command.actor_id,
            )
            await uow.commit()
            return result

    async def start_test(self, command: TestCommandInput) -> CommandResult:
        async with self._uow_factory() as uow:
            result = await uow.workflow.start_test(
                test_id=command.test_id, actor_id=command.actor_id
            )
            await uow.commit()
            return result

    async def complete_test(self, command: CompleteTestInput) -> CommandResult:
        async with self._uow_factory() as uow:
            result = await uow.workflow.complete_test(
                test_id=command.test_id,
                actor_id=command.actor_id,
                value=command.value,
                norm=command.norm,
                comment=command.comment,
            )
            await uow.commit()
            return result

    async def requeue_test(self, command: TestCommandInput) -> CommandResult:
        async with self._uow_factory() as uow:
            result = await uow.workflow.requeue_test(
                test_id=command.test_id,
                actor_id=command.actor_id,
            )
            await uow.commit()
            return result

    async def reject_test(self, command: TestCommandInput) -> CommandResult:
        async with self._uow_factory() as uow:
            result = await uow.workflow.reject_test(
                test_id=command.test_id,
                actor_id=command.actor_id,
                reason=command.reason or "",
            )
            await uow.commit()
            return result

    async def close_sample(self, command: CloseSampleInput) -> CommandResult:
        async with self._uow_factory() as uow:
            result = await uow.workflow.close_sample(
                sample_id=command.sample_id,
                actor_id=command.actor_id,
                verdict=command.verdict,
                comment=command.comment,
            )
            await uow.commit()
            return result

    async def create_protocol(self, command: CreateProtocolInput) -> CommandResult:
        async with self._uow_factory() as uow:
            result = await uow.workflow.create_protocol(
                actor_id=command.actor_id,
                sample_ids=command.sample_ids,
                protocol_type_id=command.protocol_type_id,
                conclusion_id=command.conclusion_id,
                copies=command.copies,
            )
            await uow.commit()
            return result

    async def update_protocol(self, command: UpdateProtocolInput) -> CommandResult:
        async with self._uow_factory() as uow:
            result = await uow.workflow.update_protocol(
                protocol_id=command.protocol_id,
                actor_id=command.actor_id,
                protocol_type_id=command.protocol_type_id,
                conclusion_id=command.conclusion_id,
                copies=command.copies,
            )
            await uow.commit()
            return result

    async def issue_protocol(self, command: IssueProtocolInput) -> CommandResult:
        async with self._uow_factory() as uow:
            result = await uow.workflow.issue_protocol(
                protocol_id=command.protocol_id,
                actor_id=command.actor_id,
                issued_at=command.issued_at,
            )
            await uow.commit()
            return result

    async def _publish_events(self, uow: UnitOfWork) -> None:
        events = getattr(uow.workflow, "events", [])
        if not events:
            return
        await NotificationService(repository=uow.notifications).create_from_events(events)
