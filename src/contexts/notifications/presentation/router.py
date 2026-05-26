from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from src.core.pagination import PageMeta, PaginationDependency, PaginationParams
from src.core.responses import ListResponse, ResponseMeta, SingleResponse

router = APIRouter(tags=["notifications"])


class AlertCommandRequest(BaseModel):
    actor_id: UUID


class AlertCommandResult(BaseModel):
    id: UUID | None = None
    affected: int = 0


def _meta(params: PaginationParams) -> PageMeta:
    return PageMeta(
        total=0,
        limit=params.limit,
        has_more=False,
        includes_requested=params.includes_requested,
        includes_applied=[],
        includes_allowed=[],
    )


@router.get("/alerts")
async def list_alerts(
    params: PaginationDependency,
) -> ListResponse[dict[str, object]]:
    return ListResponse(items=[], meta=_meta(params))


@router.post("/alerts/{alert_id}/mark-read")
async def mark_alert_read(
    alert_id: UUID,
    request: AlertCommandRequest,
) -> SingleResponse[AlertCommandResult]:
    return SingleResponse(
        data=AlertCommandResult(id=alert_id, affected=1),
        meta=ResponseMeta(operation="alerts.mark_read"),
    )


@router.post("/alerts/{alert_id}/hide")
async def hide_alert(
    alert_id: UUID,
    request: AlertCommandRequest,
) -> SingleResponse[AlertCommandResult]:
    return SingleResponse(
        data=AlertCommandResult(id=alert_id, affected=1),
        meta=ResponseMeta(operation="alerts.hide"),
    )


@router.post("/alerts/mark-all-read")
async def mark_all_alerts_read(request: AlertCommandRequest) -> SingleResponse[AlertCommandResult]:
    return SingleResponse(
        data=AlertCommandResult(affected=0),
        meta=ResponseMeta(operation="alerts.mark_all_read"),
    )
