from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response, status
from pydantic import BaseModel, field_serializer
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.notifications.application.push_ports import PushSubscriptionStore
from src.contexts.notifications.infrastructure.push_subscription_repository import (
    SqlAlchemyPushSubscriptionStore,
)
from src.core.config import get_settings
from src.core.database import get_db_session
from src.core.responses import ResponseMeta, SingleResponse
from src.presentation.http.access_control.dependencies import get_current_user_id

router = APIRouter(tags=["push"])


class VapidPublicKeyResponse(BaseModel):
    public_key: str


class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionRequest(BaseModel):
    endpoint: str
    keys: PushSubscriptionKeys


class PushUnsubscribeRequest(BaseModel):
    endpoint: str


class PushSubscriptionItem(BaseModel):
    id: UUID
    endpoint: str

    @field_serializer("id")
    def serialize_id(self, value: UUID) -> str:
        return str(value)


async def get_push_subscription_store(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PushSubscriptionStore:
    return SqlAlchemyPushSubscriptionStore(session=session)


@router.get("/push/vapid-public-key")
async def get_vapid_public_key() -> VapidPublicKeyResponse:
    return VapidPublicKeyResponse(public_key=get_settings().vapid_public_key)


@router.post("/push/subscriptions", status_code=status.HTTP_201_CREATED)
async def create_push_subscription(
    request: PushSubscriptionRequest,
    store: Annotated[PushSubscriptionStore, Depends(get_push_subscription_store)],
    viewer_id: Annotated[UUID, Depends(get_current_user_id)],
    user_agent: Annotated[str | None, Header()] = None,
) -> SingleResponse[PushSubscriptionItem]:
    record = await store.upsert(
        user_id=viewer_id,
        endpoint=request.endpoint,
        p256dh=request.keys.p256dh,
        auth=request.keys.auth,
        user_agent=user_agent,
    )
    return SingleResponse(
        data=PushSubscriptionItem(id=record.id, endpoint=record.endpoint),
        meta=ResponseMeta(operation="push.subscribe"),
    )


@router.delete("/push/subscriptions", status_code=status.HTTP_204_NO_CONTENT)
async def delete_push_subscription(
    request: PushUnsubscribeRequest,
    store: Annotated[PushSubscriptionStore, Depends(get_push_subscription_store)],
    _viewer_id: Annotated[UUID, Depends(get_current_user_id)],
) -> Response:
    await store.delete_by_endpoint(request.endpoint)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
