from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from starlette.requests import Request

from src.api.dependencies import get_role_permissions_service
from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.schemas import (
    RolePermissionCreateDTO,
    RolePermissionCreateEnvelopeDTO,
    RolePermissionDeleteEnvelopeDTO,
    RolePermissionListEnvelopeDTO,
    RolePermissionReadEnvelopeDTO,
    RolePermissionUpdateDTO,
    RolePermissionUpdateEnvelopeDTO,
)
from src.schemas.base import DeleteRequestDTO
from src.schemas.common import SortOrder
from src.services.role_permissions_service import RolePermissionService

router = APIRouter(prefix="/role_permissions", tags=["role_permissions"])


@router.post(
    "", response_model=RolePermissionCreateEnvelopeDTO, status_code=status.HTTP_201_CREATED
)
async def create_role_permissions(
    payload: RolePermissionCreateDTO,
    service: RolePermissionService = Depends(get_role_permissions_service),
) -> RolePermissionCreateEnvelopeDTO:
    return await service.create(payload)


@router.get("/{entity_id}", response_model=RolePermissionReadEnvelopeDTO)
async def get_role_permissions(
    entity_id: UUID,
    include: str | None = Query(default=None),
    service: RolePermissionService = Depends(get_role_permissions_service),
) -> RolePermissionReadEnvelopeDTO:
    return await service.get(entity_id, includes=parse_includes(include))


@router.get("", response_model=RolePermissionListEnvelopeDTO)
async def list_role_permissions(
    request: Request,
    service: RolePermissionService = Depends(get_role_permissions_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=500),
    sort_by: str = Query(default="id"),
    sort_order: SortOrder = Query(default="desc"),
    include: str | None = Query(default=None),
) -> RolePermissionListEnvelopeDTO:
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


@router.patch("/{entity_id}", response_model=RolePermissionUpdateEnvelopeDTO)
async def update_role_permissions(
    entity_id: UUID,
    payload: RolePermissionUpdateDTO,
    service: RolePermissionService = Depends(get_role_permissions_service),
) -> RolePermissionUpdateEnvelopeDTO:
    return await service.update(entity_id, payload)


@router.delete("/{entity_id}", response_model=RolePermissionDeleteEnvelopeDTO)
async def delete_role_permissions(
    entity_id: UUID,
    payload: DeleteRequestDTO | None = Body(default=None),
    service: RolePermissionService = Depends(get_role_permissions_service),
) -> RolePermissionDeleteEnvelopeDTO:
    reason = payload.reason if payload is not None else None
    return await service.delete(entity_id, reason=reason)
