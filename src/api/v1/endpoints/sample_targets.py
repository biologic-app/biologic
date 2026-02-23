from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from starlette.requests import Request

from src.api.dependencies import get_sample_targets_service
from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.schemas import (
    SampleTargetCreateDTO,
    SampleTargetCreateEnvelopeDTO,
    SampleTargetDeleteEnvelopeDTO,
    SampleTargetListEnvelopeDTO,
    SampleTargetReadEnvelopeDTO,
    SampleTargetUpdateDTO,
    SampleTargetUpdateEnvelopeDTO,
)
from src.schemas.base import DeleteRequestDTO
from src.schemas.common import SortOrder
from src.services.sample_targets_service import SampleTargetService

router = APIRouter(prefix="/sample_targets", tags=["sample_targets"])


@router.post("", response_model=SampleTargetCreateEnvelopeDTO, status_code=status.HTTP_201_CREATED)
async def create_sample_targets(
    payload: SampleTargetCreateDTO,
    service: SampleTargetService = Depends(get_sample_targets_service),
) -> SampleTargetCreateEnvelopeDTO:
    return await service.create(payload)


@router.get("/{entity_id}", response_model=SampleTargetReadEnvelopeDTO)
async def get_sample_targets(
    entity_id: UUID,
    include: str | None = Query(default=None),
    service: SampleTargetService = Depends(get_sample_targets_service),
) -> SampleTargetReadEnvelopeDTO:
    return await service.get(entity_id, includes=parse_includes(include))


@router.get("", response_model=SampleTargetListEnvelopeDTO)
async def list_sample_targets(
    request: Request,
    service: SampleTargetService = Depends(get_sample_targets_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=500),
    sort_by: str = Query(default="created_at"),
    sort_order: SortOrder = Query(default="desc"),
    include: str | None = Query(default=None),
) -> SampleTargetListEnvelopeDTO:
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


@router.patch("/{entity_id}", response_model=SampleTargetUpdateEnvelopeDTO)
async def update_sample_targets(
    entity_id: UUID,
    payload: SampleTargetUpdateDTO,
    service: SampleTargetService = Depends(get_sample_targets_service),
) -> SampleTargetUpdateEnvelopeDTO:
    return await service.update(entity_id, payload)


@router.delete("/{entity_id}", response_model=SampleTargetDeleteEnvelopeDTO)
async def delete_sample_targets(
    entity_id: UUID,
    payload: DeleteRequestDTO | None = Body(default=None),
    service: SampleTargetService = Depends(get_sample_targets_service),
) -> SampleTargetDeleteEnvelopeDTO:
    reason = payload.reason if payload is not None else None
    return await service.delete(entity_id, reason=reason)
