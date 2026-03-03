from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from starlette.requests import Request

from src.api.dependencies import get_direction_statuses_service
from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.schemas import (
    DirectionStatusCreateDTO,
    DirectionStatusCreateEnvelopeDTO,
    DirectionStatusDeleteEnvelopeDTO,
    DirectionStatusListEnvelopeDTO,
    DirectionStatusReadEnvelopeDTO,
    DirectionStatusUpdateDTO,
    DirectionStatusUpdateEnvelopeDTO,
)
from src.schemas.base import DeleteRequestDTO
from src.schemas.common import SortOrder
from src.services.direction_statuses_service import DirectionStatusService

router = APIRouter(prefix="/direction_statuses", tags=["direction_statuses"])


@router.post(
    "", response_model=DirectionStatusCreateEnvelopeDTO, status_code=status.HTTP_201_CREATED
)
async def create_direction_statuses(
    payload: DirectionStatusCreateDTO,
    service: DirectionStatusService = Depends(get_direction_statuses_service),
) -> DirectionStatusCreateEnvelopeDTO:
    return await service.create(payload)


@router.get("/{entity_id}", response_model=DirectionStatusReadEnvelopeDTO)
async def get_direction_statuses(
    entity_id: UUID,
    include: str | None = Query(default=None),
    service: DirectionStatusService = Depends(get_direction_statuses_service),
) -> DirectionStatusReadEnvelopeDTO:
    return await service.get(entity_id, includes=parse_includes(include))


@router.get("", response_model=DirectionStatusListEnvelopeDTO)
async def list_direction_statuses(
    request: Request,
    service: DirectionStatusService = Depends(get_direction_statuses_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=500),
    sort_by: str = Query(default="created_at"),
    sort_order: SortOrder = Query(default="desc"),
    include: str | None = Query(default=None),
) -> DirectionStatusListEnvelopeDTO:
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


@router.patch("/{entity_id}", response_model=DirectionStatusUpdateEnvelopeDTO)
async def update_direction_statuses(
    entity_id: UUID,
    payload: DirectionStatusUpdateDTO,
    service: DirectionStatusService = Depends(get_direction_statuses_service),
) -> DirectionStatusUpdateEnvelopeDTO:
    return await service.update(entity_id, payload)


@router.delete("/{entity_id}", response_model=DirectionStatusDeleteEnvelopeDTO)
async def delete_direction_statuses(
    entity_id: UUID,
    payload: DeleteRequestDTO | None = Body(default=None),
    service: DirectionStatusService = Depends(get_direction_statuses_service),
) -> DirectionStatusDeleteEnvelopeDTO:
    reason = payload.reason if payload is not None else None
    return await service.delete(entity_id, reason=reason)
