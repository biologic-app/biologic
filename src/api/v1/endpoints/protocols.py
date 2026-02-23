from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from starlette.requests import Request

from src.api.dependencies import get_protocols_service
from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.schemas import (
    ProtocolCreateDTO,
    ProtocolCreateEnvelopeDTO,
    ProtocolDeleteEnvelopeDTO,
    ProtocolListEnvelopeDTO,
    ProtocolReadEnvelopeDTO,
    ProtocolUpdateDTO,
    ProtocolUpdateEnvelopeDTO,
)
from src.schemas.base import DeleteRequestDTO
from src.schemas.common import SortOrder
from src.services.protocols_service import ProtocolService

router = APIRouter(prefix="/protocols", tags=["protocols"])


@router.post("", response_model=ProtocolCreateEnvelopeDTO, status_code=status.HTTP_201_CREATED)
async def create_protocols(
    payload: ProtocolCreateDTO, service: ProtocolService = Depends(get_protocols_service)
) -> ProtocolCreateEnvelopeDTO:
    return await service.create(payload)


@router.get("/{entity_id}", response_model=ProtocolReadEnvelopeDTO)
async def get_protocols(
    entity_id: UUID,
    include: str | None = Query(default=None),
    service: ProtocolService = Depends(get_protocols_service),
) -> ProtocolReadEnvelopeDTO:
    return await service.get(entity_id, includes=parse_includes(include))


@router.get("", response_model=ProtocolListEnvelopeDTO)
async def list_protocols(
    request: Request,
    service: ProtocolService = Depends(get_protocols_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=500),
    sort_by: str = Query(default="created_at"),
    sort_order: SortOrder = Query(default="desc"),
    include: str | None = Query(default=None),
) -> ProtocolListEnvelopeDTO:
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


@router.patch("/{entity_id}", response_model=ProtocolUpdateEnvelopeDTO)
async def update_protocols(
    entity_id: UUID,
    payload: ProtocolUpdateDTO,
    service: ProtocolService = Depends(get_protocols_service),
) -> ProtocolUpdateEnvelopeDTO:
    return await service.update(entity_id, payload)


@router.delete("/{entity_id}", response_model=ProtocolDeleteEnvelopeDTO)
async def delete_protocols(
    entity_id: UUID,
    payload: DeleteRequestDTO | None = Body(default=None),
    service: ProtocolService = Depends(get_protocols_service),
) -> ProtocolDeleteEnvelopeDTO:
    reason = payload.reason if payload is not None else None
    return await service.delete(entity_id, reason=reason)
