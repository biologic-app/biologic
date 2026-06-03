from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.dashboard.application.service import DashboardUseCase
from src.contexts.dashboard.infrastructure.repositories import SqlAlchemyDashboardRepository
from src.core.database import get_db_session
from src.core.responses import SingleResponse

router = APIRouter(tags=["dashboard"])

DashboardPeriod = Literal["daily", "weekly", "monthly"]


async def get_dashboard_use_case(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DashboardUseCase:
    return DashboardUseCase(
        repository=SqlAlchemyDashboardRepository(session=session),
    )


@router.get("/dashboard/summary")
async def dashboard_summary(
    use_case: Annotated[DashboardUseCase, Depends(get_dashboard_use_case)],
    date_from: date,
    date_to: date,
    period: DashboardPeriod = "daily",
) -> SingleResponse[dict[str, object]]:
    return await use_case.summary(
        date_from=date_from,
        date_to=date_to,
        period=period,
    )
