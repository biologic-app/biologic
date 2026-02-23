from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from starlette.requests import Request

from src.api.dependencies import get_user_roles_service
from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.schemas import (
    UserRoleCreateDTO,
    UserRoleCreateEnvelopeDTO,
    UserRoleDeleteEnvelopeDTO,
    UserRoleListEnvelopeDTO,
    UserRoleReadEnvelopeDTO,
    UserRoleUpdateDTO,
    UserRoleUpdateEnvelopeDTO,
)
from src.schemas.base import DeleteRequestDTO
from src.schemas.common import SortOrder
from src.services.user_roles_service import UserRoleService

router = APIRouter(prefix="/user_roles", tags=["user_roles"])


@router.post("", response_model=UserRoleCreateEnvelopeDTO, status_code=status.HTTP_201_CREATED)
async def create_user_roles(
    payload: UserRoleCreateDTO, service: UserRoleService = Depends(get_user_roles_service)
) -> UserRoleCreateEnvelopeDTO:
    return await service.create(payload)


@router.get("/{entity_id}", response_model=UserRoleReadEnvelopeDTO)
async def get_user_roles(
    entity_id: UUID,
    include: str | None = Query(default=None),
    service: UserRoleService = Depends(get_user_roles_service),
) -> UserRoleReadEnvelopeDTO:
    return await service.get(entity_id, includes=parse_includes(include))


@router.get("", response_model=UserRoleListEnvelopeDTO)
async def list_user_roles(
    request: Request,
    service: UserRoleService = Depends(get_user_roles_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=500),
    sort_by: str = Query(default="created_at"),
    sort_order: SortOrder = Query(default="desc"),
    include: str | None = Query(default=None),
) -> UserRoleListEnvelopeDTO:
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


@router.patch("/{entity_id}", response_model=UserRoleUpdateEnvelopeDTO)
async def update_user_roles(
    entity_id: UUID,
    payload: UserRoleUpdateDTO,
    service: UserRoleService = Depends(get_user_roles_service),
) -> UserRoleUpdateEnvelopeDTO:
    return await service.update(entity_id, payload)


@router.delete("/{entity_id}", response_model=UserRoleDeleteEnvelopeDTO)
async def delete_user_roles(
    entity_id: UUID,
    payload: DeleteRequestDTO | None = Body(default=None),
    service: UserRoleService = Depends(get_user_roles_service),
) -> UserRoleDeleteEnvelopeDTO:
    reason = payload.reason if payload is not None else None
    return await service.delete(entity_id, reason=reason)
