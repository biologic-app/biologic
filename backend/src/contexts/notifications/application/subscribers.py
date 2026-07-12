"""Subscriber side of the publisher/subscriber mechanism (see
src.core.events.EventPublisher): reacts to laboratory_workflow domain events
by creating a notification targeted at the specific user who should see it,
instead of broadcasting to everyone.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from typing import Protocol
from uuid import UUID

from src.contexts.laboratory_workflow.domain.events import DomainEvent
from src.contexts.notifications.application.service import NotificationRecord
from src.contexts.notifications.domain.contracts import NotificationDraft, notification_from_event


class NotificationTargetResolver(Protocol):
    """Resolves which users a notification about an entity should reach.

    Implemented by SqlAlchemyWorkflowRepository.resolve_notification_targets —
    kept as a narrow Protocol here so this context doesn't depend on the
    workflow context's infrastructure, only on this one capability.
    """

    async def resolve_notification_targets(
        self, entity_type: str, entity_id: UUID
    ) -> set[UUID]: ...


class NotificationSink(Protocol):
    """The one write capability this subscriber needs — narrower than the
    full NotificationRepository port (list/mark_read are irrelevant here),
    per the interface segregation principle."""

    async def create_many(
        self, drafts: Iterable[NotificationDraft]
    ) -> list[NotificationRecord]: ...


class WorkflowNotificationSubscriber:
    """Subscribes to workflow domain events and persists one targeted
    notification per resolved follower. Skips events with no configured
    notification (see notification_from_event) or no resolvable followers —
    an event for an entity nobody follows yet creates no notification, rather
    than falling back to broadcasting it to every user.
    """

    def __init__(
        self,
        *,
        repository: NotificationSink,
        resolver: NotificationTargetResolver,
    ) -> None:
        self._repository = repository
        self._resolver = resolver

    async def __call__(self, event: DomainEvent) -> None:
        draft = notification_from_event(event)
        if draft is None:
            return

        target_user_ids = await self._resolver.resolve_notification_targets(
            event.entity_type, event.entity_id
        )
        if not target_user_ids:
            return

        await self._repository.create_many(
            [replace(draft, target_user_id=uid) for uid in target_user_ids]
        )
