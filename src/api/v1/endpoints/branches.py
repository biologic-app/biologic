from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from starlette.requests import Request

from src.api.dependencies import get_branches_service
from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.schemas import (
    BranchCreateDTO,
    BranchCreateEnvelopeDTO,
    BranchDeleteEnvelopeDTO,
    BranchListEnvelopeDTO,
    BranchReadEnvelopeDTO,
    BranchUpdateDTO,
    BranchUpdateEnvelopeDTO,
)
from src.schemas.base import DeleteRequestDTO
from src.schemas.common import SortOrder
from src.services.branches_service import BranchService

router = APIRouter(prefix="/branches", tags=["branches"])


@router.post("", response_model=BranchCreateEnvelopeDTO, status_code=status.HTTP_201_CREATED)
async def create_branches(
    payload: BranchCreateDTO, service: BranchService = Depends(get_branches_service)
) -> BranchCreateEnvelopeDTO:
    return await service.create(payload)


@router.get("/{entity_id}", response_model=BranchReadEnvelopeDTO)
async def get_branches(
    entity_id: UUID,
    include: str | None = Query(default=None),
    service: BranchService = Depends(get_branches_service),
) -> BranchReadEnvelopeDTO:
    return await service.get(entity_id, includes=parse_includes(include))


@router.get("", response_model=BranchListEnvelopeDTO)
async def list_branches(
    request: Request,
    service: BranchService = Depends(get_branches_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=500),
    sort_by: str = Query(default="created_at"),
    sort_order: SortOrder = Query(default="desc"),
    include: str | None = Query(default=None),
) -> BranchListEnvelopeDTO:
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


@router.patch("/{entity_id}", response_model=BranchUpdateEnvelopeDTO)
async def update_branches(
    entity_id: UUID,
    payload: BranchUpdateDTO,
    service: BranchService = Depends(get_branches_service),
) -> BranchUpdateEnvelopeDTO:
    return await service.update(entity_id, payload)


@router.delete("/{entity_id}", response_model=BranchDeleteEnvelopeDTO)
async def delete_branches(
    entity_id: UUID,
    payload: DeleteRequestDTO | None = Body(default=None),
    service: BranchService = Depends(get_branches_service),
) -> BranchDeleteEnvelopeDTO:
    reason = payload.reason if payload is not None else None
    return await service.delete(entity_id, reason=reason)
