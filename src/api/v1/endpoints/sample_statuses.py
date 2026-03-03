from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from starlette.requests import Request

from src.api.dependencies import get_sample_statuses_service
from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.schemas import (
    SampleStatusCreateDTO,
    SampleStatusCreateEnvelopeDTO,
    SampleStatusDeleteEnvelopeDTO,
    SampleStatusListEnvelopeDTO,
    SampleStatusReadEnvelopeDTO,
    SampleStatusUpdateDTO,
    SampleStatusUpdateEnvelopeDTO,
)
from src.schemas.base import DeleteRequestDTO
from src.schemas.common import SortOrder
from src.services.sample_statuses_service import SampleStatusService

router = APIRouter(prefix="/sample_statuses", tags=["sample_statuses"])


@router.post("", response_model=SampleStatusCreateEnvelopeDTO, status_code=status.HTTP_201_CREATED)
async def create_sample_statuses(
    payload: SampleStatusCreateDTO,
    service: SampleStatusService = Depends(get_sample_statuses_service),
) -> SampleStatusCreateEnvelopeDTO:
    return await service.create(payload)


@router.get("/{entity_id}", response_model=SampleStatusReadEnvelopeDTO)
async def get_sample_statuses(
    entity_id: UUID,
    include: str | None = Query(default=None),
    service: SampleStatusService = Depends(get_sample_statuses_service),
) -> SampleStatusReadEnvelopeDTO:
    return await service.get(entity_id, includes=parse_includes(include))


@router.get("", response_model=SampleStatusListEnvelopeDTO)
async def list_sample_statuses(
    request: Request,
    service: SampleStatusService = Depends(get_sample_statuses_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=500),
    sort_by: str = Query(default="created_at"),
    sort_order: SortOrder = Query(default="desc"),
    include: str | None = Query(default=None),
) -> SampleStatusListEnvelopeDTO:
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


@router.patch("/{entity_id}", response_model=SampleStatusUpdateEnvelopeDTO)
async def update_sample_statuses(
    entity_id: UUID,
    payload: SampleStatusUpdateDTO,
    service: SampleStatusService = Depends(get_sample_statuses_service),
) -> SampleStatusUpdateEnvelopeDTO:
    return await service.update(entity_id, payload)


@router.delete("/{entity_id}", response_model=SampleStatusDeleteEnvelopeDTO)
async def delete_sample_statuses(
    entity_id: UUID,
    payload: DeleteRequestDTO | None = Body(default=None),
    service: SampleStatusService = Depends(get_sample_statuses_service),
) -> SampleStatusDeleteEnvelopeDTO:
    reason = payload.reason if payload is not None else None
    return await service.delete(entity_id, reason=reason)
