from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from starlette.requests import Request

from src.api.dependencies import get_labs_service
from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.schemas import (
    LabCreateDTO,
    LabCreateEnvelopeDTO,
    LabDeleteEnvelopeDTO,
    LabListEnvelopeDTO,
    LabReadEnvelopeDTO,
    LabUpdateDTO,
    LabUpdateEnvelopeDTO,
)
from src.schemas.base import DeleteRequestDTO
from src.schemas.common import SortOrder
from src.services.labs_service import LabService

router = APIRouter(prefix="/labs", tags=["labs"])


@router.post("", response_model=LabCreateEnvelopeDTO, status_code=status.HTTP_201_CREATED)
async def create_labs(
    payload: LabCreateDTO, service: LabService = Depends(get_labs_service)
) -> LabCreateEnvelopeDTO:
    return await service.create(payload)


@router.get("/{entity_id}", response_model=LabReadEnvelopeDTO)
async def get_labs(
    entity_id: UUID,
    include: str | None = Query(default=None),
    service: LabService = Depends(get_labs_service),
) -> LabReadEnvelopeDTO:
    return await service.get(entity_id, includes=parse_includes(include))


@router.get("", response_model=LabListEnvelopeDTO)
async def list_labs(
    request: Request,
    service: LabService = Depends(get_labs_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=500),
    sort_by: str = Query(default="created_at"),
    sort_order: SortOrder = Query(default="desc"),
    include: str | None = Query(default=None),
) -> LabListEnvelopeDTO:
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


@router.patch("/{entity_id}", response_model=LabUpdateEnvelopeDTO)
async def update_labs(
    entity_id: UUID, payload: LabUpdateDTO, service: LabService = Depends(get_labs_service)
) -> LabUpdateEnvelopeDTO:
    return await service.update(entity_id, payload)


@router.delete("/{entity_id}", response_model=LabDeleteEnvelopeDTO)
async def delete_labs(
    entity_id: UUID,
    payload: DeleteRequestDTO | None = Body(default=None),
    service: LabService = Depends(get_labs_service),
) -> LabDeleteEnvelopeDTO:
    reason = payload.reason if payload is not None else None
    return await service.delete(entity_id, reason=reason)
