from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_serializer
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.notifications.application.service import NotificationRecord, NotificationService
from src.contexts.notifications.infrastructure.repositories import SqlAlchemyNotificationRepository
from src.core.database import get_db_session
from src.core.pagination import PageMeta, PaginationDependency, PaginationParams
from src.core.responses import ListResponse, ResponseMeta, SingleResponse
from src.presentation.http.access_control.dependencies import get_current_user_id

router = APIRouter(tags=["notifications"])

AlertStatus = Literal["unread", "read", "all"]


class AlertCommandRequest(BaseModel):
    actor_id: UUID


class AlertItem(BaseModel):
    id: UUID
    kind: str
    title: str
    message: str
    entity_type: str
    entity_id: UUID
    source_event_type: str
    payload: dict[str, object]
    read_at: datetime | None
    created_at: datetime
    target_user_id: UUID | None
    target_role_key: str | None

    @field_serializer("id", "entity_id", "target_user_id")
    def serialize_uuid(self, value: UUID | None) -> str | None:
        return str(value) if value else None

    @field_serializer("read_at", "created_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return _iso_z(value)


async def get_notification_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NotificationService:
    return NotificationService(
        repository=SqlAlchemyNotificationRepository(session=session),
    )


def _meta(params: PaginationParams, *, total: int) -> PageMeta:
    return PageMeta(
        total=total,
        limit=params.limit,
        has_more=False,
        includes_requested=params.includes_requested,
        includes_applied=[],
        includes_allowed=[],
    )


@router.get("/alerts")
async def list_alerts(
    params: PaginationDependency,
    service: Annotated[NotificationService, Depends(get_notification_service)],
    viewer_id: Annotated[UUID, Depends(get_current_user_id)],
    status: AlertStatus = "unread",
) -> ListResponse[AlertItem]:
    records, total = await service.list_notifications(
        params=params, status=status, viewer_id=viewer_id
    )
    return ListResponse(
        items=[_item(record) for record in records],
        meta=_meta(params, total=total),
    )


@router.post("/alerts/{alert_id}/mark-read")
async def mark_alert_read(
    alert_id: UUID,
    request: AlertCommandRequest,
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> SingleResponse[AlertItem]:
    record = await service.mark_read(alert_id)
    return SingleResponse(
        data=_item(record),
        meta=ResponseMeta(operation="alerts.mark_read"),
    )


@router.get("/alerts/stream")
async def stream_alerts(
    request: Request,
    service: Annotated[NotificationService, Depends(get_notification_service)],
    viewer_id: Annotated[UUID, Depends(get_current_user_id)],
) -> StreamingResponse:
    shutdown = getattr(request.app.state, "shutdown_event", None)
    return StreamingResponse(
        _notification_stream(service, viewer_id, shutdown),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _item(record: NotificationRecord) -> AlertItem:
    return AlertItem(
        id=record.id,
        kind=record.kind,
        title=record.title,
        message=record.message,
        entity_type=record.entity_type,
        entity_id=record.entity_id,
        source_event_type=record.source_event_type,
        payload=record.payload,
        read_at=record.read_at,
        created_at=record.created_at,
        target_user_id=record.target_user_id,
        target_role_key=record.target_role_key,
    )


async def _notification_stream(
    service: NotificationService,
    viewer_id: UUID,
    shutdown: asyncio.Event | None = None,
) -> AsyncIterator[str]:
    async for record in service.stream_after(
        last_seen=datetime.now(UTC),
        viewer_id=viewer_id,
        poll_interval_seconds=1.0,
        shutdown=shutdown,
    ):
        yield _sse_event("notification.created", _item(record))


def _sse_event(event: str, item: AlertItem) -> str:
    data = item.model_dump_json()
    return f"event: {event}\ndata: {data}\n\n"


def _iso_z(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
