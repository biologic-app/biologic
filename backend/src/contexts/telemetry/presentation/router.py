from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.telemetry.application.service import TelemetryService
from src.contexts.telemetry.domain.contracts import TelemetryEventDraft
from src.contexts.telemetry.infrastructure.repositories import SqlAlchemyTelemetryRepository
from src.core.database import get_db_session
from src.core.responses import ResponseMeta, SingleResponse

router = APIRouter(tags=["telemetry"])

# Fire-and-forget batches from the browser: cap batch size so a runaway
# client buffer can't turn one request into an unbounded write.
MAX_BATCH_SIZE = 200


class TelemetryEventIn(BaseModel):
    """A single anonymous UI event. Only element/session identifiers are
    accepted — no form values or other user-entered content (ROADMAP A2.3).
    """

    event: str
    route: str
    session_id: str
    ts: datetime
    element_id: str | None = None
    # Role is supplied by the client from its own auth state — telemetry
    # ingestion intentionally stays unauthenticated (fire-and-forget), so it
    # is not re-derived from a session here.
    role: str | None = None


class TelemetryBatchIn(BaseModel):
    events: list[TelemetryEventIn] = Field(min_length=1, max_length=MAX_BATCH_SIZE)


async def get_telemetry_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TelemetryService:
    return TelemetryService(repository=SqlAlchemyTelemetryRepository(session=session))


@router.post("/telemetry/events", status_code=status.HTTP_202_ACCEPTED)
async def record_telemetry_events(
    batch: TelemetryBatchIn,
    service: Annotated[TelemetryService, Depends(get_telemetry_service)],
) -> SingleResponse[dict[str, int]]:
    drafts = [
        TelemetryEventDraft(
            event=item.event,
            route=item.route,
            session_id=item.session_id,
            ts=item.ts,
            element_id=item.element_id,
            role=item.role,
        )
        for item in batch.events
    ]
    accepted = await service.record_events(drafts)
    return SingleResponse(
        data={"accepted": accepted},
        meta=ResponseMeta(operation="telemetry.record_events"),
    )
