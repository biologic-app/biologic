from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.released_samples.service import ReleasedSamplesUseCase
from src.core.database import get_db_session
from src.core.responses import SingleResponse
from src.infrastructure.repositories.released_samples import (
    SqlAlchemyReleasedSamplesRepository,
)

router = APIRouter(tags=["directions"])


class ReleasedObjectInfo(BaseModel):
    name: str | None = None
    code: str | None = None


class ReleasedDirectionInfo(BaseModel):
    id: UUID
    year_no: int | None = None
    base_no: int | None = None
    doctor: str | None = None
    object: ReleasedObjectInfo


class ReleasedSampleItem(BaseModel):
    id: UUID
    name: str | None = None
    status_code: str | None = None
    status_name: str | None = None
    sample_type_name: str | None = None
    protocol_id: UUID | None = None
    completed_at: datetime | None = None


class ReleasedDirectionGroup(BaseModel):
    direction: ReleasedDirectionInfo
    samples: list[ReleasedSampleItem]
    released_count: int
    total_count: int
    all_released: bool


async def get_released_samples_use_case(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ReleasedSamplesUseCase:
    return ReleasedSamplesUseCase(
        repository=SqlAlchemyReleasedSamplesRepository(session=session),
    )


@router.get("/directions/released-samples")
async def directions_released_samples(
    use_case: Annotated[ReleasedSamplesUseCase, Depends(get_released_samples_use_case)],
) -> SingleResponse[list[ReleasedDirectionGroup]]:
    result = await use_case.released_by_direction()
    return SingleResponse[list[ReleasedDirectionGroup]](
        data=[ReleasedDirectionGroup.model_validate(item) for item in result.data],
        meta=result.meta,
    )
