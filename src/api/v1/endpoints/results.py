from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from starlette.requests import Request

from src.api.dependencies import get_results_service
from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.schemas import (
    ResultCreateDTO,
    ResultCreateEnvelopeDTO,
    ResultDeleteEnvelopeDTO,
    ResultListEnvelopeDTO,
    ResultReadEnvelopeDTO,
    ResultUpdateDTO,
    ResultUpdateEnvelopeDTO,
)
from src.schemas.base import DeleteRequestDTO
from src.schemas.common import SortOrder
from src.services.results_service import ResultService

router = APIRouter(prefix="/results", tags=["results"])


@router.post("", response_model=ResultCreateEnvelopeDTO, status_code=status.HTTP_201_CREATED)
async def create_results(
    payload: ResultCreateDTO, service: ResultService = Depends(get_results_service)
) -> ResultCreateEnvelopeDTO:
    return await service.create(payload)


@router.get("/{entity_id}", response_model=ResultReadEnvelopeDTO)
async def get_results(
    entity_id: UUID,
    include: str | None = Query(default=None),
    service: ResultService = Depends(get_results_service),
) -> ResultReadEnvelopeDTO:
    return await service.get(entity_id, includes=parse_includes(include))


@router.get("", response_model=ResultListEnvelopeDTO)
async def list_results(
    request: Request,
    service: ResultService = Depends(get_results_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=500),
    sort_by: str = Query(default="created_at"),
    sort_order: SortOrder = Query(default="desc"),
    include: str | None = Query(default=None),
) -> ResultListEnvelopeDTO:
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


@router.patch("/{entity_id}", response_model=ResultUpdateEnvelopeDTO)
async def update_results(
    entity_id: UUID, payload: ResultUpdateDTO, service: ResultService = Depends(get_results_service)
) -> ResultUpdateEnvelopeDTO:
    return await service.update(entity_id, payload)


@router.delete("/{entity_id}", response_model=ResultDeleteEnvelopeDTO)
async def delete_results(
    entity_id: UUID,
    payload: DeleteRequestDTO | None = Body(default=None),
    service: ResultService = Depends(get_results_service),
) -> ResultDeleteEnvelopeDTO:
    reason = payload.reason if payload is not None else None
    return await service.delete(entity_id, reason=reason)
