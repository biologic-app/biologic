from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from starlette.requests import Request

from src.api.dependencies import get_tests_service
from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.schemas import (
    TestCreateDTO,
    TestCreateEnvelopeDTO,
    TestDeleteEnvelopeDTO,
    TestListEnvelopeDTO,
    TestReadEnvelopeDTO,
    TestUpdateDTO,
    TestUpdateEnvelopeDTO,
)
from src.schemas.base import DeleteRequestDTO
from src.schemas.common import SortOrder
from src.services.tests_service import TestService

router = APIRouter(prefix="/tests", tags=["tests"])


@router.post("", response_model=TestCreateEnvelopeDTO, status_code=status.HTTP_201_CREATED)
async def create_tests(
    payload: TestCreateDTO, service: TestService = Depends(get_tests_service)
) -> TestCreateEnvelopeDTO:
    return await service.create(payload)


@router.get("/{entity_id}", response_model=TestReadEnvelopeDTO)
async def get_tests(
    entity_id: UUID,
    include: str | None = Query(default=None),
    service: TestService = Depends(get_tests_service),
) -> TestReadEnvelopeDTO:
    return await service.get(entity_id, includes=parse_includes(include))


@router.get("", response_model=TestListEnvelopeDTO)
async def list_tests(
    request: Request,
    service: TestService = Depends(get_tests_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=500),
    sort_by: str = Query(default="created_at"),
    sort_order: SortOrder = Query(default="desc"),
    include: str | None = Query(default=None),
) -> TestListEnvelopeDTO:
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


@router.patch("/{entity_id}", response_model=TestUpdateEnvelopeDTO)
async def update_tests(
    entity_id: UUID, payload: TestUpdateDTO, service: TestService = Depends(get_tests_service)
) -> TestUpdateEnvelopeDTO:
    return await service.update(entity_id, payload)


@router.delete("/{entity_id}", response_model=TestDeleteEnvelopeDTO)
async def delete_tests(
    entity_id: UUID,
    payload: DeleteRequestDTO | None = Body(default=None),
    service: TestService = Depends(get_tests_service),
) -> TestDeleteEnvelopeDTO:
    reason = payload.reason if payload is not None else None
    return await service.delete(entity_id, reason=reason)
