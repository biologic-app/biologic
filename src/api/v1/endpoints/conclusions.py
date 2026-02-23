from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from starlette.requests import Request

from src.api.dependencies import get_conclusions_service
from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.schemas import (
    ConclusionCreateDTO,
    ConclusionCreateEnvelopeDTO,
    ConclusionDeleteEnvelopeDTO,
    ConclusionListEnvelopeDTO,
    ConclusionReadEnvelopeDTO,
    ConclusionUpdateDTO,
    ConclusionUpdateEnvelopeDTO,
)
from src.schemas.base import DeleteRequestDTO
from src.schemas.common import SortOrder
from src.services.conclusions_service import ConclusionService

router = APIRouter(prefix="/conclusions", tags=["conclusions"])


@router.post("", response_model=ConclusionCreateEnvelopeDTO, status_code=status.HTTP_201_CREATED)
async def create_conclusions(
    payload: ConclusionCreateDTO, service: ConclusionService = Depends(get_conclusions_service)
) -> ConclusionCreateEnvelopeDTO:
    return await service.create(payload)


@router.get("/{entity_id}", response_model=ConclusionReadEnvelopeDTO)
async def get_conclusions(
    entity_id: UUID,
    include: str | None = Query(default=None),
    service: ConclusionService = Depends(get_conclusions_service),
) -> ConclusionReadEnvelopeDTO:
    return await service.get(entity_id, includes=parse_includes(include))


@router.get("", response_model=ConclusionListEnvelopeDTO)
async def list_conclusions(
    request: Request,
    service: ConclusionService = Depends(get_conclusions_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=500),
    sort_by: str = Query(default="created_at"),
    sort_order: SortOrder = Query(default="desc"),
    include: str | None = Query(default=None),
) -> ConclusionListEnvelopeDTO:
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


@router.patch("/{entity_id}", response_model=ConclusionUpdateEnvelopeDTO)
async def update_conclusions(
    entity_id: UUID,
    payload: ConclusionUpdateDTO,
    service: ConclusionService = Depends(get_conclusions_service),
) -> ConclusionUpdateEnvelopeDTO:
    return await service.update(entity_id, payload)


@router.delete("/{entity_id}", response_model=ConclusionDeleteEnvelopeDTO)
async def delete_conclusions(
    entity_id: UUID,
    payload: DeleteRequestDTO | None = Body(default=None),
    service: ConclusionService = Depends(get_conclusions_service),
) -> ConclusionDeleteEnvelopeDTO:
    reason = payload.reason if payload is not None else None
    return await service.delete(entity_id, reason=reason)
