from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from starlette.requests import Request

from src.api.dependencies import get_permissions_service
from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.schemas import (
    PermissionCreateDTO,
    PermissionCreateEnvelopeDTO,
    PermissionDeleteEnvelopeDTO,
    PermissionListEnvelopeDTO,
    PermissionReadEnvelopeDTO,
    PermissionUpdateDTO,
    PermissionUpdateEnvelopeDTO,
)
from src.schemas.base import DeleteRequestDTO
from src.schemas.common import SortOrder
from src.services.permissions_service import PermissionService

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.post("", response_model=PermissionCreateEnvelopeDTO, status_code=status.HTTP_201_CREATED)
async def create_permissions(
    payload: PermissionCreateDTO, service: PermissionService = Depends(get_permissions_service)
) -> PermissionCreateEnvelopeDTO:
    return await service.create(payload)


@router.get("/{entity_id}", response_model=PermissionReadEnvelopeDTO)
async def get_permissions(
    entity_id: UUID,
    include: str | None = Query(default=None),
    service: PermissionService = Depends(get_permissions_service),
) -> PermissionReadEnvelopeDTO:
    return await service.get(entity_id, includes=parse_includes(include))


@router.get("", response_model=PermissionListEnvelopeDTO)
async def list_permissions(
    request: Request,
    service: PermissionService = Depends(get_permissions_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=500),
    sort_by: str = Query(default="id"),
    sort_order: SortOrder = Query(default="desc"),
    include: str | None = Query(default=None),
) -> PermissionListEnvelopeDTO:
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


@router.patch("/{entity_id}", response_model=PermissionUpdateEnvelopeDTO)
async def update_permissions(
    entity_id: UUID,
    payload: PermissionUpdateDTO,
    service: PermissionService = Depends(get_permissions_service),
) -> PermissionUpdateEnvelopeDTO:
    return await service.update(entity_id, payload)


@router.delete("/{entity_id}", response_model=PermissionDeleteEnvelopeDTO)
async def delete_permissions(
    entity_id: UUID,
    payload: DeleteRequestDTO | None = Body(default=None),
    service: PermissionService = Depends(get_permissions_service),
) -> PermissionDeleteEnvelopeDTO:
    reason = payload.reason if payload is not None else None
    return await service.delete(entity_id, reason=reason)
