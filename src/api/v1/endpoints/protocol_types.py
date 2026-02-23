from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from starlette.requests import Request

from src.api.dependencies import get_protocol_types_service
from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.schemas import (
    ProtocolTypeCreateDTO,
    ProtocolTypeCreateEnvelopeDTO,
    ProtocolTypeDeleteEnvelopeDTO,
    ProtocolTypeListEnvelopeDTO,
    ProtocolTypeReadEnvelopeDTO,
    ProtocolTypeUpdateDTO,
    ProtocolTypeUpdateEnvelopeDTO,
)
from src.schemas.base import DeleteRequestDTO
from src.schemas.common import SortOrder
from src.services.protocol_types_service import ProtocolTypeService

router = APIRouter(prefix="/protocol_types", tags=["protocol_types"])


@router.post("", response_model=ProtocolTypeCreateEnvelopeDTO, status_code=status.HTTP_201_CREATED)
async def create_protocol_types(
    payload: ProtocolTypeCreateDTO,
    service: ProtocolTypeService = Depends(get_protocol_types_service),
) -> ProtocolTypeCreateEnvelopeDTO:
    return await service.create(payload)


@router.get("/{entity_id}", response_model=ProtocolTypeReadEnvelopeDTO)
async def get_protocol_types(
    entity_id: UUID,
    include: str | None = Query(default=None),
    service: ProtocolTypeService = Depends(get_protocol_types_service),
) -> ProtocolTypeReadEnvelopeDTO:
    return await service.get(entity_id, includes=parse_includes(include))


@router.get("", response_model=ProtocolTypeListEnvelopeDTO)
async def list_protocol_types(
    request: Request,
    service: ProtocolTypeService = Depends(get_protocol_types_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=500),
    sort_by: str = Query(default="created_at"),
    sort_order: SortOrder = Query(default="desc"),
    include: str | None = Query(default=None),
) -> ProtocolTypeListEnvelopeDTO:
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


@router.patch("/{entity_id}", response_model=ProtocolTypeUpdateEnvelopeDTO)
async def update_protocol_types(
    entity_id: UUID,
    payload: ProtocolTypeUpdateDTO,
    service: ProtocolTypeService = Depends(get_protocol_types_service),
) -> ProtocolTypeUpdateEnvelopeDTO:
    return await service.update(entity_id, payload)


@router.delete("/{entity_id}", response_model=ProtocolTypeDeleteEnvelopeDTO)
async def delete_protocol_types(
    entity_id: UUID,
    payload: DeleteRequestDTO | None = Body(default=None),
    service: ProtocolTypeService = Depends(get_protocol_types_service),
) -> ProtocolTypeDeleteEnvelopeDTO:
    reason = payload.reason if payload is not None else None
    return await service.delete(entity_id, reason=reason)
