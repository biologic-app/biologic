from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel

from src.core.responses import ResponseMeta, SingleResponse
from src.core.status_codes import DIRECTION_DRAFT, SAMPLE_PENDING


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


# --- registrar dashboard (role-specific, intake-focused read model) ---


class StatusCount(BaseModel):
    """One row of a lifecycle-status breakdown (e.g. directions in `draft`).

    `id` is the status-table UUID — the value the list pages filter on
    (`status_id`), so the dashboard can deep-link a card to the filtered list.
    """

    id: UUID
    code: str | None
    count: int
    color: str | None = None


class RegistrarKpis(BaseModel):
    """Headline numbers for the intake desk. Org-wide (the dashboard reports on
    what the lab received, not who keyed it in — `created_by` is technical).

    `directions_draft` / `samples_pending` are the intake queue (what still needs
    registering); `*_received_today` count rows whose `received_at` falls on the
    current day; `urgent_open` is urgent, not-done directions + samples.
    """

    directions_draft: int
    samples_pending: int
    urgent_open: int
    directions_received_today: int
    samples_received_today: int


class RecentDirection(BaseModel):
    id: UUID
    year_no: int | None
    base_no: int | None
    status_code: str | None
    status_color: str | None = None
    is_urgent: bool
    received_at: datetime | None


class TimelineBucket(BaseModel):
    """One time bucket of sample intake, bucketed by `received_at`. `by_status`
    maps every sample-status code to how many of the bucket's received samples
    currently sit in that status, so the whole lifecycle (including defects) is
    visible over time."""

    bucket_start: date
    by_status: dict[str, int]


class LabStatusCount(BaseModel):
    """Samples assigned to a laboratory, broken down by current status — the two
    levels of the nested donut (lab → status)."""

    lab_id: UUID
    lab_code: str
    lab_name: str
    status_code: str | None
    status_color: str | None = None
    count: int


class RegistrarDashboard(BaseModel):
    generated_at: datetime
    kpis: RegistrarKpis
    directions_by_status: list[StatusCount]
    samples_by_status: list[StatusCount]
    samples_by_lab: list[LabStatusCount]
    recent_directions: list[RecentDirection]
    timeline: list[TimelineBucket]


RECENT_DIRECTIONS_LIMIT = 10


class RegistrarDashboardRepository(Protocol):
    async def directions_by_status(self) -> list[StatusCount]: ...

    async def samples_by_status(self) -> list[StatusCount]: ...

    async def urgent_open_total(self) -> int: ...

    async def samples_by_lab(self) -> list[LabStatusCount]: ...

    async def directions_received_between(self, *, start: datetime, end: datetime) -> int: ...

    async def samples_received_between(self, *, start: datetime, end: datetime) -> int: ...

    async def recent_directions(self, *, limit: int) -> list[RecentDirection]: ...

    async def timeline(
        self,
        *,
        date_from: date,
        date_to: date,
        period: str,
    ) -> list[TimelineBucket]: ...


def _count_for(rows: list[StatusCount], code: str) -> int:
    return next((row.count for row in rows if row.code == code), 0)


class RegistrarDashboardUseCase:
    def __init__(self, *, repository: RegistrarDashboardRepository) -> None:
        self.repository = repository

    async def summary(
        self,
        *,
        date_from: date,
        date_to: date,
        period: str,
    ) -> SingleResponse[RegistrarDashboard]:
        now = datetime.now(UTC)
        today_start = datetime(now.year, now.month, now.day, tzinfo=UTC)
        today_end = today_start + timedelta(days=1)

        directions_by_status = await self.repository.directions_by_status()
        samples_by_status = await self.repository.samples_by_status()
        samples_by_lab = await self.repository.samples_by_lab()
        urgent_open = await self.repository.urgent_open_total()
        directions_today = await self.repository.directions_received_between(
            start=today_start,
            end=today_end,
        )
        samples_today = await self.repository.samples_received_between(
            start=today_start,
            end=today_end,
        )
        recent_directions = await self.repository.recent_directions(
            limit=RECENT_DIRECTIONS_LIMIT,
        )
        timeline = await self.repository.timeline(
            date_from=date_from,
            date_to=date_to,
            period=period,
        )

        data = RegistrarDashboard(
            generated_at=now,
            kpis=RegistrarKpis(
                directions_draft=_count_for(directions_by_status, DIRECTION_DRAFT),
                samples_pending=_count_for(samples_by_status, SAMPLE_PENDING),
                urgent_open=urgent_open,
                directions_received_today=directions_today,
                samples_received_today=samples_today,
            ),
            directions_by_status=directions_by_status,
            samples_by_status=samples_by_status,
            samples_by_lab=samples_by_lab,
            recent_directions=recent_directions,
            timeline=timeline,
        )
        return SingleResponse(
            data=data,
            meta=ResponseMeta(operation="dashboard.registrar"),
        )
