from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.contexts.laboratory_workflow.domain.events import DomainEvent, StatusChanged


@dataclass(frozen=True)
class NotificationDraft:
    kind: str
    title: str
    message: str
    entity_type: str
    entity_id: UUID
    source_event_type: str
    payload: dict[str, Any]
    target_user_id: UUID | None = None
    target_role_key: str | None = None


def notification_from_event(event: DomainEvent) -> NotificationDraft | None:
    if isinstance(event, StatusChanged):
        return _notification_from_status_changed(event)
    return None


def _notification_from_status_changed(event: StatusChanged) -> NotificationDraft | None:
    if event.event_type == "DirectionRegistered":
        return _status_notification(
            event,
            kind="workflow.direction_registered",
            title="Direction registered",
            message="Direction was registered.",
        )
    if event.event_type == "SampleRegistered":
        return _status_notification(
            event,
            kind="workflow.sample_registered",
            title="Sample registered",
            message="Sample was registered.",
        )
    if event.event_type == "SampleRejected":
        reason = event.reason.strip()
        return _status_notification(
            event,
            kind="workflow.sample_rejected",
            title="Sample rejected",
            message=f"Sample was rejected. Reason: {reason}" if reason else "Sample was rejected.",
        )
    return None


def _status_notification(
    event: StatusChanged,
    *,
    kind: str,
    title: str,
    message: str,
) -> NotificationDraft:
    return NotificationDraft(
        kind=kind,
        title=title,
        message=message,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        source_event_type=event.event_type,
        payload={
            "from_code": event.from_code,
            "to_code": event.to_code,
            "reason": event.reason,
        },
    )
