from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from starlette.requests import Request

from src.api.dependencies import get_test_statuses_service
from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.schemas import (
    TestStatusCreateDTO,
    TestStatusCreateEnvelopeDTO,
    TestStatusDeleteEnvelopeDTO,
    TestStatusListEnvelopeDTO,
    TestStatusReadEnvelopeDTO,
    TestStatusUpdateDTO,
    TestStatusUpdateEnvelopeDTO,
)
from src.schemas.base import DeleteRequestDTO
from src.schemas.common import SortOrder
from src.services.test_statuses_service import TestStatusService

router = APIRouter(prefix="/test_statuses", tags=["test_statuses"])


@router.post("", response_model=TestStatusCreateEnvelopeDTO, status_code=status.HTTP_201_CREATED)
async def create_test_statuses(
    payload: TestStatusCreateDTO,
    service: TestStatusService = Depends(get_test_statuses_service),
) -> TestStatusCreateEnvelopeDTO:
    return await service.create(payload)


@router.get("/{entity_id}", response_model=TestStatusReadEnvelopeDTO)
async def get_test_statuses(
    entity_id: UUID,
    include: str | None = Query(default=None),
    service: TestStatusService = Depends(get_test_statuses_service),
) -> TestStatusReadEnvelopeDTO:
    return await service.get(entity_id, includes=parse_includes(include))


@router.get("", response_model=TestStatusListEnvelopeDTO)
async def list_test_statuses(
    request: Request,
    service: TestStatusService = Depends(get_test_statuses_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=500),
    sort_by: str = Query(default="created_at"),
    sort_order: SortOrder = Query(default="desc"),
    include: str | None = Query(default=None),
) -> TestStatusListEnvelopeDTO:
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


@router.patch("/{entity_id}", response_model=TestStatusUpdateEnvelopeDTO)
async def update_test_statuses(
    entity_id: UUID,
    payload: TestStatusUpdateDTO,
    service: TestStatusService = Depends(get_test_statuses_service),
) -> TestStatusUpdateEnvelopeDTO:
    return await service.update(entity_id, payload)


@router.delete("/{entity_id}", response_model=TestStatusDeleteEnvelopeDTO)
async def delete_test_statuses(
    entity_id: UUID,
    payload: DeleteRequestDTO | None = Body(default=None),
    service: TestStatusService = Depends(get_test_statuses_service),
) -> TestStatusDeleteEnvelopeDTO:
    reason = payload.reason if payload is not None else None
    return await service.delete(entity_id, reason=reason)
