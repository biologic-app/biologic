from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from starlette.requests import Request

from src.api.dependencies import get_objects_service
from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.schemas import (
    ObjectCreateDTO,
    ObjectCreateEnvelopeDTO,
    ObjectDeleteEnvelopeDTO,
    ObjectListEnvelopeDTO,
    ObjectReadEnvelopeDTO,
    ObjectUpdateDTO,
    ObjectUpdateEnvelopeDTO,
)
from src.schemas.base import DeleteRequestDTO
from src.schemas.common import SortOrder
from src.services.objects_service import ObjectService

router = APIRouter(prefix="/objects", tags=["objects"])


@router.post("", response_model=ObjectCreateEnvelopeDTO, status_code=status.HTTP_201_CREATED)
async def create_objects(
    payload: ObjectCreateDTO, service: ObjectService = Depends(get_objects_service)
) -> ObjectCreateEnvelopeDTO:
    return await service.create(payload)


@router.get("/{entity_id}", response_model=ObjectReadEnvelopeDTO)
async def get_objects(
    entity_id: UUID,
    include: str | None = Query(default=None),
    service: ObjectService = Depends(get_objects_service),
) -> ObjectReadEnvelopeDTO:
    return await service.get(entity_id, includes=parse_includes(include))


@router.get("", response_model=ObjectListEnvelopeDTO)
async def list_objects(
    request: Request,
    service: ObjectService = Depends(get_objects_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=500),
    sort_by: str = Query(default="created_at"),
    sort_order: SortOrder = Query(default="desc"),
    include: str | None = Query(default=None),
) -> ObjectListEnvelopeDTO:
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


@router.patch("/{entity_id}", response_model=ObjectUpdateEnvelopeDTO)
async def update_objects(
    entity_id: UUID, payload: ObjectUpdateDTO, service: ObjectService = Depends(get_objects_service)
) -> ObjectUpdateEnvelopeDTO:
    return await service.update(entity_id, payload)


@router.delete("/{entity_id}", response_model=ObjectDeleteEnvelopeDTO)
async def delete_objects(
    entity_id: UUID,
    payload: DeleteRequestDTO | None = Body(default=None),
    service: ObjectService = Depends(get_objects_service),
) -> ObjectDeleteEnvelopeDTO:
    reason = payload.reason if payload is not None else None
    return await service.delete(entity_id, reason=reason)
