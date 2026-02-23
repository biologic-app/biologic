from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from starlette.requests import Request

from src.api.dependencies import get_samples_service
from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.schemas import (
    SampleCreateDTO,
    SampleCreateEnvelopeDTO,
    SampleDeleteEnvelopeDTO,
    SampleListEnvelopeDTO,
    SampleReadEnvelopeDTO,
    SampleUpdateDTO,
    SampleUpdateEnvelopeDTO,
)
from src.schemas.base import DeleteRequestDTO
from src.schemas.common import SortOrder
from src.services.samples_service import SampleService

router = APIRouter(prefix="/samples", tags=["samples"])


@router.post("", response_model=SampleCreateEnvelopeDTO, status_code=status.HTTP_201_CREATED)
async def create_samples(
    payload: SampleCreateDTO, service: SampleService = Depends(get_samples_service)
) -> SampleCreateEnvelopeDTO:
    return await service.create(payload)


@router.get("/{entity_id}", response_model=SampleReadEnvelopeDTO)
async def get_samples(
    entity_id: UUID,
    include: str | None = Query(default=None),
    service: SampleService = Depends(get_samples_service),
) -> SampleReadEnvelopeDTO:
    return await service.get(entity_id, includes=parse_includes(include))


@router.get("", response_model=SampleListEnvelopeDTO)
async def list_samples(
    request: Request,
    service: SampleService = Depends(get_samples_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=500),
    sort_by: str = Query(default="created_at"),
    sort_order: SortOrder = Query(default="desc"),
    include: str | None = Query(default=None),
) -> SampleListEnvelopeDTO:
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


@router.patch("/{entity_id}", response_model=SampleUpdateEnvelopeDTO)
async def update_samples(
    entity_id: UUID, payload: SampleUpdateDTO, service: SampleService = Depends(get_samples_service)
) -> SampleUpdateEnvelopeDTO:
    return await service.update(entity_id, payload)


@router.delete("/{entity_id}", response_model=SampleDeleteEnvelopeDTO)
async def delete_samples(
    entity_id: UUID,
    payload: DeleteRequestDTO | None = Body(default=None),
    service: SampleService = Depends(get_samples_service),
) -> SampleDeleteEnvelopeDTO:
    reason = payload.reason if payload is not None else None
    return await service.delete(entity_id, reason=reason)
