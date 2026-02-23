from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from starlette.requests import Request

from src.api.dependencies import get_research_goals_service
from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.schemas import (
    ResearchGoalCreateDTO,
    ResearchGoalCreateEnvelopeDTO,
    ResearchGoalDeleteEnvelopeDTO,
    ResearchGoalListEnvelopeDTO,
    ResearchGoalReadEnvelopeDTO,
    ResearchGoalUpdateDTO,
    ResearchGoalUpdateEnvelopeDTO,
)
from src.schemas.base import DeleteRequestDTO
from src.schemas.common import SortOrder
from src.services.research_goals_service import ResearchGoalService

router = APIRouter(prefix="/research_goals", tags=["research_goals"])


@router.post("", response_model=ResearchGoalCreateEnvelopeDTO, status_code=status.HTTP_201_CREATED)
async def create_research_goals(
    payload: ResearchGoalCreateDTO,
    service: ResearchGoalService = Depends(get_research_goals_service),
) -> ResearchGoalCreateEnvelopeDTO:
    return await service.create(payload)


@router.get("/{entity_id}", response_model=ResearchGoalReadEnvelopeDTO)
async def get_research_goals(
    entity_id: UUID,
    include: str | None = Query(default=None),
    service: ResearchGoalService = Depends(get_research_goals_service),
) -> ResearchGoalReadEnvelopeDTO:
    return await service.get(entity_id, includes=parse_includes(include))


@router.get("", response_model=ResearchGoalListEnvelopeDTO)
async def list_research_goals(
    request: Request,
    service: ResearchGoalService = Depends(get_research_goals_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=500),
    sort_by: str = Query(default="created_at"),
    sort_order: SortOrder = Query(default="desc"),
    include: str | None = Query(default=None),
) -> ResearchGoalListEnvelopeDTO:
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


@router.patch("/{entity_id}", response_model=ResearchGoalUpdateEnvelopeDTO)
async def update_research_goals(
    entity_id: UUID,
    payload: ResearchGoalUpdateDTO,
    service: ResearchGoalService = Depends(get_research_goals_service),
) -> ResearchGoalUpdateEnvelopeDTO:
    return await service.update(entity_id, payload)


@router.delete("/{entity_id}", response_model=ResearchGoalDeleteEnvelopeDTO)
async def delete_research_goals(
    entity_id: UUID,
    payload: DeleteRequestDTO | None = Body(default=None),
    service: ResearchGoalService = Depends(get_research_goals_service),
) -> ResearchGoalDeleteEnvelopeDTO:
    reason = payload.reason if payload is not None else None
    return await service.delete(entity_id, reason=reason)
