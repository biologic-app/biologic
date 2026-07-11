from datetime import UTC, datetime
from uuid import UUID

from fakes import FakeUnitOfWork, WorkflowRepositoryFake, fake_uow_factory

from src.contexts.laboratory_workflow.application.commands import WorkflowCommandService
from src.contexts.laboratory_workflow.application.dto import CommandResult, RegisterSampleInput
from src.contexts.laboratory_workflow.domain.events import StatusChanged
from src.contexts.notifications.application.service import NotificationRecord

SAMPLE_ID = UUID("00000000-0000-0000-0000-000000000f01")
ACTOR_ID = UUID("00000000-0000-0000-0000-000000000f02")
TARGET_USER_ID = UUID("00000000-0000-0000-0000-000000000f03")

RECORD = NotificationRecord(
    id=UUID("00000000-0000-0000-0000-000000000f04"),
    kind="workflow.sample_registered",
    title="Sample registered",
    message="Sample was registered.",
    entity_type="samples",
    entity_id=SAMPLE_ID,
    source_event_type="SampleRegistered",
    payload={},
    read_at=None,
    created_at=datetime(2026, 7, 10, 9, 0, tzinfo=UTC),
    target_user_id=TARGET_USER_ID,
    target_role_key=None,
)


class FakeWorkflowRepositoryWithEvents(WorkflowRepositoryFake):
    def __init__(self) -> None:
        self.events = [
            StatusChanged(
                entity_type="samples",
                entity_id=SAMPLE_ID,
                event_type="SampleRegistered",
                from_code="pending",
                to_code="registered",
                reason="",
            ),
        ]

    async def register_sample(
        self,
        sample_id: UUID,
        actor_id: UUID,
        received_at: datetime,
        deadline: datetime | None,
    ) -> CommandResult:
        return CommandResult(
            id=sample_id,
            status_id=UUID("00000000-0000-0000-0000-000000000f05"),
            updated_at=datetime(2026, 7, 10, 9, 0, tzinfo=UTC),
        )

    async def resolve_notification_target(
        self, entity_type: str, entity_id: UUID
    ) -> UUID | None:
        return TARGET_USER_ID


class FakeNotificationRepository:
    async def create_many(self, drafts: object) -> list[NotificationRecord]:
        return [RECORD]


class SpyPushDispatcher:
    def __init__(self, uow: FakeUnitOfWork) -> None:
        self._uow = uow
        self.dispatched: list[list[NotificationRecord]] = []
        self.committed_when_dispatched: list[bool] = []

    def dispatch(self, records: list[NotificationRecord]) -> None:
        self.dispatched.append(list(records))
        self.committed_when_dispatched.append(self._uow.committed)


async def test_push_is_dispatched_with_the_committed_notification_after_commit() -> None:
    workflow = FakeWorkflowRepositoryWithEvents()
    uow = FakeUnitOfWork(workflow)
    uow.notifications = FakeNotificationRepository()  # type: ignore[assignment]
    dispatcher = SpyPushDispatcher(uow)
    service = WorkflowCommandService(
        uow_factory=fake_uow_factory(uow),
        push_dispatcher=dispatcher,  # type: ignore[arg-type]
    )

    await service.register_sample(
        RegisterSampleInput(
            sample_id=SAMPLE_ID,
            actor_id=ACTOR_ID,
            received_at=datetime(2026, 7, 10, 9, 0, tzinfo=UTC),
            deadline=None,
        ),
    )

    assert dispatcher.dispatched == [[RECORD]]
    # The dispatcher must only ever see a dispatch call once uow.commit() has
    # already run — pushing before commit would notify for a change that
    # might still roll back.
    assert dispatcher.committed_when_dispatched == [True]


async def test_no_push_dispatch_without_a_configured_dispatcher() -> None:
    workflow = FakeWorkflowRepositoryWithEvents()
    uow = FakeUnitOfWork(workflow)
    uow.notifications = FakeNotificationRepository()  # type: ignore[assignment]
    service = WorkflowCommandService(uow_factory=fake_uow_factory(uow))

    result = await service.register_sample(
        RegisterSampleInput(
            sample_id=SAMPLE_ID,
            actor_id=ACTOR_ID,
            received_at=datetime(2026, 7, 10, 9, 0, tzinfo=UTC),
            deadline=None,
        ),
    )

    assert result.id == SAMPLE_ID
    assert uow.committed
