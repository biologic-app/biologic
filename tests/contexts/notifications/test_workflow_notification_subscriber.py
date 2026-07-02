from collections.abc import Iterable
from uuid import UUID

from src.contexts.laboratory_workflow.domain.events import DomainEvent, StatusChanged
from src.contexts.notifications.application.service import NotificationRecord
from src.contexts.notifications.application.subscribers import WorkflowNotificationSubscriber
from src.contexts.notifications.domain.contracts import NotificationDraft
from src.core.events import EventPublisher

OWNER_ID = UUID("00000000-0000-0000-0000-000000000e01")
SAMPLE_ID = UUID("00000000-0000-0000-0000-000000000e02")


class RecordingNotificationRepository:
    def __init__(self) -> None:
        self.created: list[NotificationDraft] = []

    async def create_many(
        self, drafts: Iterable[NotificationDraft]
    ) -> list[NotificationRecord]:
        drafts = list(drafts)
        self.created.extend(drafts)
        return []


class StaticResolver:
    def __init__(self, target: UUID | None) -> None:
        self.target = target
        self.calls: list[tuple[str, UUID]] = []

    async def resolve_notification_target(self, entity_type: str, entity_id: UUID) -> UUID | None:
        self.calls.append((entity_type, entity_id))
        return self.target


async def test_subscriber_targets_the_resolved_owner_not_everyone() -> None:
    repository = RecordingNotificationRepository()
    resolver = StaticResolver(OWNER_ID)
    subscriber = WorkflowNotificationSubscriber(repository=repository, resolver=resolver)

    await subscriber(
        StatusChanged(
            entity_type="samples",
            entity_id=SAMPLE_ID,
            event_type="SampleRejected",
            from_code="pending",
            to_code="rejected",
            reason="Container damaged",
        ),
    )

    assert resolver.calls == [("samples", SAMPLE_ID)]
    assert len(repository.created) == 1
    draft = repository.created[0]
    assert draft.target_user_id == OWNER_ID
    assert draft.kind == "workflow.sample_rejected"


async def test_subscriber_skips_notification_when_owner_cannot_be_resolved() -> None:
    repository = RecordingNotificationRepository()
    resolver = StaticResolver(None)
    subscriber = WorkflowNotificationSubscriber(repository=repository, resolver=resolver)

    await subscriber(
        StatusChanged(
            entity_type="samples",
            entity_id=SAMPLE_ID,
            event_type="SampleRejected",
            from_code="pending",
            to_code="rejected",
            reason="Container damaged",
        ),
    )

    assert repository.created == []


async def test_subscriber_ignores_events_with_no_notification_mapping() -> None:
    repository = RecordingNotificationRepository()
    resolver = StaticResolver(OWNER_ID)
    subscriber = WorkflowNotificationSubscriber(repository=repository, resolver=resolver)

    await subscriber(
        DomainEvent(
            entity_type="samples",
            entity_id=SAMPLE_ID,
            event_type="InternalAuditOnly",
        ),
    )

    assert repository.created == []
    assert resolver.calls == []


async def test_event_publisher_delivers_to_every_subscriber_in_order() -> None:
    publisher = EventPublisher()
    seen: list[str] = []

    async def first(event: DomainEvent) -> None:
        seen.append(f"first:{event.event_type}")

    async def second(event: DomainEvent) -> None:
        seen.append(f"second:{event.event_type}")

    publisher.subscribe(first)
    publisher.subscribe(second)

    await publisher.publish_all(
        [
            DomainEvent(entity_type="samples", entity_id=SAMPLE_ID, event_type="A"),
            DomainEvent(entity_type="samples", entity_id=SAMPLE_ID, event_type="B"),
        ],
    )

    assert seen == ["first:A", "second:A", "first:B", "second:B"]
