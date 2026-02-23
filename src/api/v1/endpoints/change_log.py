from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from starlette.requests import Request

from src.api.dependencies import get_change_log_service
from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.schemas import (
    ChangeLogCreateDTO,
    ChangeLogCreateEnvelopeDTO,
    ChangeLogDeleteEnvelopeDTO,
    ChangeLogListEnvelopeDTO,
    ChangeLogReadEnvelopeDTO,
    ChangeLogUpdateDTO,
    ChangeLogUpdateEnvelopeDTO,
)
from src.schemas.base import DeleteRequestDTO
from src.schemas.common import SortOrder
from src.services.change_log_service import ChangeLogService

router = APIRouter(prefix="/change_log", tags=["change_log"])


@router.post("", response_model=ChangeLogCreateEnvelopeDTO, status_code=status.HTTP_201_CREATED)
async def create_change_log(
    payload: ChangeLogCreateDTO, service: ChangeLogService = Depends(get_change_log_service)
) -> ChangeLogCreateEnvelopeDTO:
    return await service.create(payload)


@router.get("/{entity_id}", response_model=ChangeLogReadEnvelopeDTO)
async def get_change_log(
    entity_id: UUID,
    include: str | None = Query(default=None),
    service: ChangeLogService = Depends(get_change_log_service),
) -> ChangeLogReadEnvelopeDTO:
    return await service.get(entity_id, includes=parse_includes(include))


@router.get("", response_model=ChangeLogListEnvelopeDTO)
async def list_change_log(
    request: Request,
    service: ChangeLogService = Depends(get_change_log_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=500),
    sort_by: str = Query(default="created_at"),
    sort_order: SortOrder = Query(default="desc"),
    include: str | None = Query(default=None),
) -> ChangeLogListEnvelopeDTO:
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


@router.patch("/{entity_id}", response_model=ChangeLogUpdateEnvelopeDTO)
async def update_change_log(
    entity_id: UUID,
    payload: ChangeLogUpdateDTO,
    service: ChangeLogService = Depends(get_change_log_service),
) -> ChangeLogUpdateEnvelopeDTO:
    return await service.update(entity_id, payload)


@router.delete("/{entity_id}", response_model=ChangeLogDeleteEnvelopeDTO)
async def delete_change_log(
    entity_id: UUID,
    payload: DeleteRequestDTO | None = Body(default=None),
    service: ChangeLogService = Depends(get_change_log_service),
) -> ChangeLogDeleteEnvelopeDTO:
    reason = payload.reason if payload is not None else None
    return await service.delete(entity_id, reason=reason)
