from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from starlette.requests import Request

from src.api.dependencies import get_sample_types_service
from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.schemas import (
    SampleTypeCreateDTO,
    SampleTypeCreateEnvelopeDTO,
    SampleTypeDeleteEnvelopeDTO,
    SampleTypeListEnvelopeDTO,
    SampleTypeReadEnvelopeDTO,
    SampleTypeUpdateDTO,
    SampleTypeUpdateEnvelopeDTO,
)
from src.schemas.base import DeleteRequestDTO
from src.schemas.common import SortOrder
from src.services.sample_types_service import SampleTypeService

router = APIRouter(prefix="/sample_types", tags=["sample_types"])


@router.post("", response_model=SampleTypeCreateEnvelopeDTO, status_code=status.HTTP_201_CREATED)
async def create_sample_types(
    payload: SampleTypeCreateDTO, service: SampleTypeService = Depends(get_sample_types_service)
) -> SampleTypeCreateEnvelopeDTO:
    return await service.create(payload)


@router.get("/{entity_id}", response_model=SampleTypeReadEnvelopeDTO)
async def get_sample_types(
    entity_id: UUID,
    include: str | None = Query(default=None),
    service: SampleTypeService = Depends(get_sample_types_service),
) -> SampleTypeReadEnvelopeDTO:
    return await service.get(entity_id, includes=parse_includes(include))


@router.get("", response_model=SampleTypeListEnvelopeDTO)
async def list_sample_types(
    request: Request,
    service: SampleTypeService = Depends(get_sample_types_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=500),
    sort_by: str = Query(default="created_at"),
    sort_order: SortOrder = Query(default="desc"),
    include: str | None = Query(default=None),
) -> SampleTypeListEnvelopeDTO:
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


@router.patch("/{entity_id}", response_model=SampleTypeUpdateEnvelopeDTO)
async def update_sample_types(
    entity_id: UUID,
    payload: SampleTypeUpdateDTO,
    service: SampleTypeService = Depends(get_sample_types_service),
) -> SampleTypeUpdateEnvelopeDTO:
    return await service.update(entity_id, payload)


@router.delete("/{entity_id}", response_model=SampleTypeDeleteEnvelopeDTO)
async def delete_sample_types(
    entity_id: UUID,
    payload: DeleteRequestDTO | None = Body(default=None),
    service: SampleTypeService = Depends(get_sample_types_service),
) -> SampleTypeDeleteEnvelopeDTO:
    reason = payload.reason if payload is not None else None
    return await service.delete(entity_id, reason=reason)
