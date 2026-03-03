from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from starlette.requests import Request

from src.api.dependencies import get_research_service
from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.schemas import (
    ResearchCreateDTO,
    ResearchCreateEnvelopeDTO,
    ResearchDeleteEnvelopeDTO,
    ResearchListEnvelopeDTO,
    ResearchReadEnvelopeDTO,
    ResearchUpdateDTO,
    ResearchUpdateEnvelopeDTO,
)
from src.schemas.base import DeleteRequestDTO
from src.schemas.common import SortOrder
from src.services.research_service import ResearchService

router = APIRouter(prefix="/research", tags=["research"])


@router.post("", response_model=ResearchCreateEnvelopeDTO, status_code=status.HTTP_201_CREATED)
async def create_research(
    payload: ResearchCreateDTO, service: ResearchService = Depends(get_research_service)
) -> ResearchCreateEnvelopeDTO:
    return await service.create(payload)


@router.get("/{entity_id}", response_model=ResearchReadEnvelopeDTO)
async def get_research(
    entity_id: UUID,
    include: str | None = Query(default=None),
    service: ResearchService = Depends(get_research_service),
) -> ResearchReadEnvelopeDTO:
    return await service.get(entity_id, includes=parse_includes(include))


@router.get("", response_model=ResearchListEnvelopeDTO)
async def list_research(
    request: Request,
    service: ResearchService = Depends(get_research_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=500),
    sort_by: str = Query(default="created_at"),
    sort_order: SortOrder = Query(default="desc"),
    include: str | None = Query(default=None),
) -> ResearchListEnvelopeDTO:
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


@router.patch("/{entity_id}", response_model=ResearchUpdateEnvelopeDTO)
async def update_research(
    entity_id: UUID,
    payload: ResearchUpdateDTO,
    service: ResearchService = Depends(get_research_service),
) -> ResearchUpdateEnvelopeDTO:
    return await service.update(entity_id, payload)


@router.delete("/{entity_id}", response_model=ResearchDeleteEnvelopeDTO)
async def delete_research(
    entity_id: UUID,
    payload: DeleteRequestDTO | None = Body(default=None),
    service: ResearchService = Depends(get_research_service),
) -> ResearchDeleteEnvelopeDTO:
    reason = payload.reason if payload is not None else None
    return await service.delete(entity_id, reason=reason)
