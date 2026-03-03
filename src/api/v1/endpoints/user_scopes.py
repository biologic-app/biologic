from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from starlette.requests import Request

from src.api.dependencies import get_user_scopes_service
from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.schemas import (
    UserScopeCreateDTO,
    UserScopeCreateEnvelopeDTO,
    UserScopeDeleteEnvelopeDTO,
    UserScopeListEnvelopeDTO,
    UserScopeReadEnvelopeDTO,
    UserScopeUpdateDTO,
    UserScopeUpdateEnvelopeDTO,
)
from src.schemas.base import DeleteRequestDTO
from src.schemas.common import SortOrder
from src.services.user_scopes_service import UserScopeService

router = APIRouter(prefix="/user_scopes", tags=["user_scopes"])


@router.post("", response_model=UserScopeCreateEnvelopeDTO, status_code=status.HTTP_201_CREATED)
async def create_user_scopes(
    payload: UserScopeCreateDTO,
    service: UserScopeService = Depends(get_user_scopes_service),
) -> UserScopeCreateEnvelopeDTO:
    return await service.create(payload)


@router.get("/{entity_id}", response_model=UserScopeReadEnvelopeDTO)
async def get_user_scopes(
    entity_id: UUID,
    include: str | None = Query(default=None),
    service: UserScopeService = Depends(get_user_scopes_service),
) -> UserScopeReadEnvelopeDTO:
    return await service.get(entity_id, includes=parse_includes(include))


@router.get("", response_model=UserScopeListEnvelopeDTO)
async def list_user_scopes(
    request: Request,
    service: UserScopeService = Depends(get_user_scopes_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=500),
    sort_by: str = Query(default="id"),
    sort_order: SortOrder = Query(default="desc"),
    include: str | None = Query(default=None),
) -> UserScopeListEnvelopeDTO:
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


@router.patch("/{entity_id}", response_model=UserScopeUpdateEnvelopeDTO)
async def update_user_scopes(
    entity_id: UUID,
    payload: UserScopeUpdateDTO,
    service: UserScopeService = Depends(get_user_scopes_service),
) -> UserScopeUpdateEnvelopeDTO:
    return await service.update(entity_id, payload)


@router.delete("/{entity_id}", response_model=UserScopeDeleteEnvelopeDTO)
async def delete_user_scopes(
    entity_id: UUID,
    payload: DeleteRequestDTO | None = Body(default=None),
    service: UserScopeService = Depends(get_user_scopes_service),
) -> UserScopeDeleteEnvelopeDTO:
    reason = payload.reason if payload is not None else None
    return await service.delete(entity_id, reason=reason)
