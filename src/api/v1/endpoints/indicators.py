from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from starlette.requests import Request

from src.api.dependencies import get_indicators_service
from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.schemas import (
    IndicatorCreateDTO,
    IndicatorCreateEnvelopeDTO,
    IndicatorDeleteEnvelopeDTO,
    IndicatorListEnvelopeDTO,
    IndicatorReadEnvelopeDTO,
    IndicatorUpdateDTO,
    IndicatorUpdateEnvelopeDTO,
)
from src.schemas.base import DeleteRequestDTO
from src.schemas.common import SortOrder
from src.services.indicators_service import IndicatorService

router = APIRouter(prefix="/indicators", tags=["indicators"])


@router.post("", response_model=IndicatorCreateEnvelopeDTO, status_code=status.HTTP_201_CREATED)
async def create_indicators(
    payload: IndicatorCreateDTO, service: IndicatorService = Depends(get_indicators_service)
) -> IndicatorCreateEnvelopeDTO:
    return await service.create(payload)


@router.get("/{entity_id}", response_model=IndicatorReadEnvelopeDTO)
async def get_indicators(
    entity_id: UUID,
    include: str | None = Query(default=None),
    service: IndicatorService = Depends(get_indicators_service),
) -> IndicatorReadEnvelopeDTO:
    return await service.get(entity_id, includes=parse_includes(include))


@router.get("", response_model=IndicatorListEnvelopeDTO)
async def list_indicators(
    request: Request,
    service: IndicatorService = Depends(get_indicators_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=500),
    sort_by: str = Query(default="created_at"),
    sort_order: SortOrder = Query(default="desc"),
    include: str | None = Query(default=None),
) -> IndicatorListEnvelopeDTO:
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


@router.patch("/{entity_id}", response_model=IndicatorUpdateEnvelopeDTO)
async def update_indicators(
    entity_id: UUID,
    payload: IndicatorUpdateDTO,
    service: IndicatorService = Depends(get_indicators_service),
) -> IndicatorUpdateEnvelopeDTO:
    return await service.update(entity_id, payload)


@router.delete("/{entity_id}", response_model=IndicatorDeleteEnvelopeDTO)
async def delete_indicators(
    entity_id: UUID,
    payload: DeleteRequestDTO | None = Body(default=None),
    service: IndicatorService = Depends(get_indicators_service),
) -> IndicatorDeleteEnvelopeDTO:
    reason = payload.reason if payload is not None else None
    return await service.delete(entity_id, reason=reason)
