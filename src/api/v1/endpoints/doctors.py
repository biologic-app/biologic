from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from starlette.requests import Request

from src.api.dependencies import get_doctors_service
from src.api.v1.endpoints._helpers import parse_includes, parse_list_filters
from src.schemas import (
    DoctorCreateDTO,
    DoctorCreateEnvelopeDTO,
    DoctorDeleteEnvelopeDTO,
    DoctorListEnvelopeDTO,
    DoctorReadEnvelopeDTO,
    DoctorUpdateDTO,
    DoctorUpdateEnvelopeDTO,
)
from src.schemas.base import DeleteRequestDTO
from src.schemas.common import SortOrder
from src.services.doctors_service import DoctorService

router = APIRouter(prefix="/doctors", tags=["doctors"])


@router.post("", response_model=DoctorCreateEnvelopeDTO, status_code=status.HTTP_201_CREATED)
async def create_doctors(
    payload: DoctorCreateDTO, service: DoctorService = Depends(get_doctors_service)
) -> DoctorCreateEnvelopeDTO:
    return await service.create(payload)


@router.get("/{entity_id}", response_model=DoctorReadEnvelopeDTO)
async def get_doctors(
    entity_id: UUID,
    include: str | None = Query(default=None),
    service: DoctorService = Depends(get_doctors_service),
) -> DoctorReadEnvelopeDTO:
    return await service.get(entity_id, includes=parse_includes(include))


@router.get("", response_model=DoctorListEnvelopeDTO)
async def list_doctors(
    request: Request,
    service: DoctorService = Depends(get_doctors_service),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=500),
    sort_by: str = Query(default="created_at"),
    sort_order: SortOrder = Query(default="desc"),
    include: str | None = Query(default=None),
) -> DoctorListEnvelopeDTO:
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


@router.patch("/{entity_id}", response_model=DoctorUpdateEnvelopeDTO)
async def update_doctors(
    entity_id: UUID, payload: DoctorUpdateDTO, service: DoctorService = Depends(get_doctors_service)
) -> DoctorUpdateEnvelopeDTO:
    return await service.update(entity_id, payload)


@router.delete("/{entity_id}", response_model=DoctorDeleteEnvelopeDTO)
async def delete_doctors(
    entity_id: UUID,
    payload: DeleteRequestDTO | None = Body(default=None),
    service: DoctorService = Depends(get_doctors_service),
) -> DoctorDeleteEnvelopeDTO:
    reason = payload.reason if payload is not None else None
    return await service.delete(entity_id, reason=reason)
