from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from starlette.requests import Request

from src.api.dependencies import get_conclusion_statuses_service
from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.schemas import (
    ConclusionStatusCreateDTO,
    ConclusionStatusCreateEnvelopeDTO,
    ConclusionStatusDeleteEnvelopeDTO,
    ConclusionStatusListEnvelopeDTO,
    ConclusionStatusReadEnvelopeDTO,
    ConclusionStatusUpdateDTO,
    ConclusionStatusUpdateEnvelopeDTO,
)
from src.schemas.base import DeleteRequestDTO
from src.schemas.common import SortOrder
from src.services.conclusion_statuses_service import ConclusionStatusService

router = APIRouter(prefix="/conclusion_statuses", tags=["conclusion_statuses"])


@router.post(
    "", response_model=ConclusionStatusCreateEnvelopeDTO, status_code=status.HTTP_201_CREATED
)
async def create_conclusion_statuses(
    payload: ConclusionStatusCreateDTO,
    service: ConclusionStatusService = Depends(get_conclusion_statuses_service),
) -> ConclusionStatusCreateEnvelopeDTO:
    return await service.create(payload)


@router.get("/{entity_id}", response_model=ConclusionStatusReadEnvelopeDTO)
async def get_conclusion_statuses(
    entity_id: UUID,
    include: str | None = Query(default=None),
    service: ConclusionStatusService = Depends(get_conclusion_statuses_service),
) -> ConclusionStatusReadEnvelopeDTO:
    return await service.get(entity_id, includes=parse_includes(include))


@router.get("", response_model=ConclusionStatusListEnvelopeDTO)
async def list_conclusion_statuses(
    request: Request,
    service: ConclusionStatusService = Depends(get_conclusion_statuses_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=500),
    sort_by: str = Query(default="created_at"),
    sort_order: SortOrder = Query(default="desc"),
    include: str | None = Query(default=None),
) -> ConclusionStatusListEnvelopeDTO:
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


@router.patch("/{entity_id}", response_model=ConclusionStatusUpdateEnvelopeDTO)
async def update_conclusion_statuses(
    entity_id: UUID,
    payload: ConclusionStatusUpdateDTO,
    service: ConclusionStatusService = Depends(get_conclusion_statuses_service),
) -> ConclusionStatusUpdateEnvelopeDTO:
    return await service.update(entity_id, payload)


@router.delete("/{entity_id}", response_model=ConclusionStatusDeleteEnvelopeDTO)
async def delete_conclusion_statuses(
    entity_id: UUID,
    payload: DeleteRequestDTO | None = Body(default=None),
    service: ConclusionStatusService = Depends(get_conclusion_statuses_service),
) -> ConclusionStatusDeleteEnvelopeDTO:
    reason = payload.reason if payload is not None else None
    return await service.delete(entity_id, reason=reason)
