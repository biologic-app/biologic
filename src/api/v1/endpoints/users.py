from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from starlette.requests import Request

from src.api.dependencies import get_users_service
from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.schemas import (
    UserCreateDTO,
    UserCreateEnvelopeDTO,
    UserDeleteEnvelopeDTO,
    UserListEnvelopeDTO,
    UserReadEnvelopeDTO,
    UserUpdateDTO,
    UserUpdateEnvelopeDTO,
)
from src.schemas.base import DeleteRequestDTO
from src.schemas.common import SortOrder
from src.services.users_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserCreateEnvelopeDTO, status_code=status.HTTP_201_CREATED)
async def create_users(
    payload: UserCreateDTO, service: UserService = Depends(get_users_service)
) -> UserCreateEnvelopeDTO:
    return await service.create(payload)


@router.get("/{entity_id}", response_model=UserReadEnvelopeDTO)
async def get_users(
    entity_id: UUID,
    include: str | None = Query(default=None),
    service: UserService = Depends(get_users_service),
) -> UserReadEnvelopeDTO:
    return await service.get(entity_id, includes=parse_includes(include))


@router.get("", response_model=UserListEnvelopeDTO)
async def list_users(
    request: Request,
    service: UserService = Depends(get_users_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=500),
    sort_by: str = Query(default="created_at"),
    sort_order: SortOrder = Query(default="desc"),
    include: str | None = Query(default=None),
) -> UserListEnvelopeDTO:
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


@router.patch("/{entity_id}", response_model=UserUpdateEnvelopeDTO)
async def update_users(
    entity_id: UUID, payload: UserUpdateDTO, service: UserService = Depends(get_users_service)
) -> UserUpdateEnvelopeDTO:
    return await service.update(entity_id, payload)


@router.delete("/{entity_id}", response_model=UserDeleteEnvelopeDTO)
async def delete_users(
    entity_id: UUID,
    payload: DeleteRequestDTO | None = Body(default=None),
    service: UserService = Depends(get_users_service),
) -> UserDeleteEnvelopeDTO:
    reason = payload.reason if payload is not None else None
    return await service.delete(entity_id, reason=reason)
