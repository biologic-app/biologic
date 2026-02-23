from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from starlette.requests import Request

from src.api.dependencies import get_roles_service
from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.schemas import (
    RoleCreateDTO,
    RoleCreateEnvelopeDTO,
    RoleDeleteEnvelopeDTO,
    RoleListEnvelopeDTO,
    RoleReadEnvelopeDTO,
    RoleUpdateDTO,
    RoleUpdateEnvelopeDTO,
)
from src.schemas.base import DeleteRequestDTO
from src.schemas.common import SortOrder
from src.services.roles_service import RoleService

router = APIRouter(prefix="/roles", tags=["roles"])


@router.post("", response_model=RoleCreateEnvelopeDTO, status_code=status.HTTP_201_CREATED)
async def create_roles(
    payload: RoleCreateDTO, service: RoleService = Depends(get_roles_service)
) -> RoleCreateEnvelopeDTO:
    return await service.create(payload)


@router.get("/{entity_id}", response_model=RoleReadEnvelopeDTO)
async def get_roles(
    entity_id: UUID,
    include: str | None = Query(default=None),
    service: RoleService = Depends(get_roles_service),
) -> RoleReadEnvelopeDTO:
    return await service.get(entity_id, includes=parse_includes(include))


@router.get("", response_model=RoleListEnvelopeDTO)
async def list_roles(
    request: Request,
    service: RoleService = Depends(get_roles_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=500),
    sort_by: str = Query(default="created_at"),
    sort_order: SortOrder = Query(default="desc"),
    include: str | None = Query(default=None),
) -> RoleListEnvelopeDTO:
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


@router.patch("/{entity_id}", response_model=RoleUpdateEnvelopeDTO)
async def update_roles(
    entity_id: UUID, payload: RoleUpdateDTO, service: RoleService = Depends(get_roles_service)
) -> RoleUpdateEnvelopeDTO:
    return await service.update(entity_id, payload)


@router.delete("/{entity_id}", response_model=RoleDeleteEnvelopeDTO)
async def delete_roles(
    entity_id: UUID,
    payload: DeleteRequestDTO | None = Body(default=None),
    service: RoleService = Depends(get_roles_service),
) -> RoleDeleteEnvelopeDTO:
    reason = payload.reason if payload is not None else None
    return await service.delete(entity_id, reason=reason)
