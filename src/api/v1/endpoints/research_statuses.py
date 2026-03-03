from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from starlette.requests import Request

from src.api.dependencies import get_research_statuses_service
from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.schemas import (
    ResearchStatusCreateDTO,
    ResearchStatusCreateEnvelopeDTO,
    ResearchStatusDeleteEnvelopeDTO,
    ResearchStatusListEnvelopeDTO,
    ResearchStatusReadEnvelopeDTO,
    ResearchStatusUpdateDTO,
    ResearchStatusUpdateEnvelopeDTO,
)
from src.schemas.base import DeleteRequestDTO
from src.schemas.common import SortOrder
from src.services.research_statuses_service import ResearchStatusService

router = APIRouter(prefix="/research_statuses", tags=["research_statuses"])


@router.post(
    "", response_model=ResearchStatusCreateEnvelopeDTO, status_code=status.HTTP_201_CREATED
)
async def create_research_statuses(
    payload: ResearchStatusCreateDTO,
    service: ResearchStatusService = Depends(get_research_statuses_service),
) -> ResearchStatusCreateEnvelopeDTO:
    return await service.create(payload)


@router.get("/{entity_id}", response_model=ResearchStatusReadEnvelopeDTO)
async def get_research_statuses(
    entity_id: UUID,
    include: str | None = Query(default=None),
    service: ResearchStatusService = Depends(get_research_statuses_service),
) -> ResearchStatusReadEnvelopeDTO:
    return await service.get(entity_id, includes=parse_includes(include))


@router.get("", response_model=ResearchStatusListEnvelopeDTO)
async def list_research_statuses(
    request: Request,
    service: ResearchStatusService = Depends(get_research_statuses_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=500),
    sort_by: str = Query(default="created_at"),
    sort_order: SortOrder = Query(default="desc"),
    include: str | None = Query(default=None),
) -> ResearchStatusListEnvelopeDTO:
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


@router.patch("/{entity_id}", response_model=ResearchStatusUpdateEnvelopeDTO)
async def update_research_statuses(
    entity_id: UUID,
    payload: ResearchStatusUpdateDTO,
    service: ResearchStatusService = Depends(get_research_statuses_service),
) -> ResearchStatusUpdateEnvelopeDTO:
    return await service.update(entity_id, payload)


@router.delete("/{entity_id}", response_model=ResearchStatusDeleteEnvelopeDTO)
async def delete_research_statuses(
    entity_id: UUID,
    payload: DeleteRequestDTO | None = Body(default=None),
    service: ResearchStatusService = Depends(get_research_statuses_service),
) -> ResearchStatusDeleteEnvelopeDTO:
    reason = payload.reason if payload is not None else None
    return await service.delete(entity_id, reason=reason)
