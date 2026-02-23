from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from starlette.requests import Request

from src.api.dependencies import get_statuses_service
from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.schemas import (
    StatusCreateDTO,
    StatusCreateEnvelopeDTO,
    StatusDeleteEnvelopeDTO,
    StatusListEnvelopeDTO,
    StatusReadEnvelopeDTO,
    StatusUpdateDTO,
    StatusUpdateEnvelopeDTO,
)
from src.schemas.base import DeleteRequestDTO
from src.schemas.common import SortOrder
from src.services.statuses_service import StatusService

router = APIRouter(prefix="/statuses", tags=["statuses"])


@router.post("", response_model=StatusCreateEnvelopeDTO, status_code=status.HTTP_201_CREATED)
async def create_statuses(
    payload: StatusCreateDTO, service: StatusService = Depends(get_statuses_service)
) -> StatusCreateEnvelopeDTO:
    return await service.create(payload)


@router.get("/{entity_id}", response_model=StatusReadEnvelopeDTO)
async def get_statuses(
    entity_id: UUID,
    include: str | None = Query(default=None),
    service: StatusService = Depends(get_statuses_service),
) -> StatusReadEnvelopeDTO:
    return await service.get(entity_id, includes=parse_includes(include))


@router.get("", response_model=StatusListEnvelopeDTO)
async def list_statuses(
    request: Request,
    service: StatusService = Depends(get_statuses_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=500),
    sort_by: str = Query(default="created_at"),
    sort_order: SortOrder = Query(default="desc"),
    include: str | None = Query(default=None),
) -> StatusListEnvelopeDTO:
    exact_filters, range_filters = parse_list_filters(dict(request.query_params))
    return await service.list(
        offset=offset,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        includes=parse_includes(include),
        exact_filters=exact_filters,
        range_filters=range_filters,
    )


@router.patch("/{entity_id}", response_model=StatusUpdateEnvelopeDTO)
async def update_statuses(
    entity_id: UUID,
    payload: StatusUpdateDTO,
    service: StatusService = Depends(get_statuses_service),
) -> StatusUpdateEnvelopeDTO:
    return await service.update(entity_id, payload)


@router.delete("/{entity_id}", response_model=StatusDeleteEnvelopeDTO)
async def delete_statuses(
    entity_id: UUID,
    payload: DeleteRequestDTO | None = Body(default=None),
    service: StatusService = Depends(get_statuses_service),
) -> StatusDeleteEnvelopeDTO:
    reason = payload.reason if payload is not None else None
    return await service.delete(entity_id, reason=reason)
