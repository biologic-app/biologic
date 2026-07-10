from collections.abc import Iterable
from uuid import UUID

from src.contexts.laboratory_workflow.domain.events import DomainEvent, StatusChanged
from src.contexts.notifications.application.service import NotificationRecord
from src.contexts.notifications.application.subscribers import WorkflowNotificationSubscriber
from src.contexts.notifications.domain.contracts import NotificationDraft
from src.core.events import EventPublisher

OWNER_ID = UUID("00000000-0000-0000-0000-000000000e01")
SAMPLE_ID = UUID("00000000-0000-0000-0000-000000000e02")
REGISTRAR_ID = UUID("00000000-0000-0000-0000-000000000e03")


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
    def __init__(self, targets: set[UUID]) -> None:
        self.targets = targets
        self.calls: list[tuple[str, UUID]] = []

    async def resolve_notification_targets(
        self, entity_type: str, entity_id: UUID
    ) -> set[UUID]:
        self.calls.append((entity_type, entity_id))
        return self.targets


async def test_subscriber_targets_the_resolved_followers_not_everyone() -> None:
    repository = RecordingNotificationRepository()
    resolver = StaticResolver({OWNER_ID, REGISTRAR_ID})
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
    assert len(repository.created) == 2
    assert {draft.target_user_id for draft in repository.created} == {OWNER_ID, REGISTRAR_ID}
    assert {draft.kind for draft in repository.created} == {"workflow.sample_rejected"}


async def test_subscriber_skips_notification_when_no_followers_resolve() -> None:
    repository = RecordingNotificationRepository()
    resolver = StaticResolver(set())
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
    resolver = StaticResolver({OWNER_ID})
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
