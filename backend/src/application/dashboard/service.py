from __future__ import annotations

from datetime import date
from typing import Protocol

from src.core.responses import ResponseMeta, SingleResponse


class DashboardRepository(Protocol):
    async def summary(
        self,
        *,
        date_from: date,
        date_to: date,
        period: str,
    ) -> dict[str, object]: ...


class DashboardUseCase:
    def __init__(self, *, repository: DashboardRepository) -> None:
        self.repository = repository

    async def summary(
        self,
        *,
        date_from: date,
        date_to: date,
        period: str,
    ) -> SingleResponse[dict[str, object]]:
        data = await self.repository.summary(
            date_from=date_from,
            date_to=date_to,
            period=period,
        )
        return SingleResponse(
            data=data,
            meta=ResponseMeta(operation="dashboard.summary"),
        )
