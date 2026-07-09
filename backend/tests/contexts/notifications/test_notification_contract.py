from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Table

from src.contexts.laboratory_workflow.domain.events import DomainEvent, StatusChanged
from src.contexts.notifications.domain.contracts import notification_from_event
from src.infrastructure.db.models import Notification


def test_sample_rejected_event_becomes_global_notification() -> None:
    sample_id = UUID("00000000-0000-0000-0000-000000000101")

    draft = notification_from_event(
        StatusChanged(
            entity_type="samples",
            entity_id=sample_id,
            event_type="SampleRejected",
            from_code="pending",
            to_code="rejected",
            reason="Container damaged",
        ),
    )

    assert draft is not None
    assert draft.kind == "workflow.sample_rejected"
    assert draft.title == "Sample rejected"
    assert "Container damaged" in draft.message
    assert draft.entity_type == "samples"
    assert draft.entity_id == sample_id
    assert draft.source_event_type == "SampleRejected"
    assert draft.target_user_id is None
    assert draft.target_role_key is None
    assert draft.payload["from_code"] == "pending"
    assert draft.payload["to_code"] == "rejected"


def test_unmapped_domain_event_does_not_become_notification() -> None:
    draft = notification_from_event(
        DomainEvent(
            entity_type="samples",
            entity_id=UUID("00000000-0000-0000-0000-000000000102"),
            event_type="InternalAuditOnly",
        ),
    )

    assert draft is None


def test_notification_model_has_read_at_and_future_target_columns() -> None:
    table = Notification.__table__

    assert isinstance(table, Table)
    assert "read_at" in table.columns
    assert "target_user_id" in table.columns
    assert "target_role_key" in table.columns
    assert table.columns["read_at"].nullable is True
    assert table.columns["target_user_id"].nullable is True
    assert table.columns["target_role_key"].nullable is True
    assert {idx.name for idx in table.indexes} >= {
        "notifications_notifications_created_at",
        "notifications_notifications_read_at",
    }


def test_notification_read_state_is_stored_only_as_read_at() -> None:
    notification = Notification(
        kind="workflow.sample_registered",
        title="Sample registered",
        message="Sample was registered.",
        entity_type="samples",
        entity_id=UUID("00000000-0000-0000-0000-000000000103"),
        source_event_type="SampleRegistered",
        payload={},
    )

    assert notification.read_at is None

    read_at = datetime.now(UTC)
    notification.read_at = read_at

    assert notification.read_at == read_at
