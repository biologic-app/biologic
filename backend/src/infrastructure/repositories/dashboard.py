from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dashboard.service import (
    LabStatusCount,
    RecentDirection,
    StatusCount,
    TimelineBucket,
)
from src.core.status_codes import (
    DIRECTION_COMPLETED,
    DIRECTION_DRAFT,
    DIRECTION_IN_PROGRESS,
    DIRECTION_PARTIALLY_COMPLETED,
    DIRECTION_REGISTERED,
    SAMPLE_ANALYZED,
    SAMPLE_COMPLETED,
    SAMPLE_IN_PROGRESS,
    SAMPLE_PENDING,
    SAMPLE_REGISTERED,
    SAMPLE_REJECTED,
)
from src.infrastructure.db.models import (
    Direction,
    DirectionStatus,
    Lab,
    Sample,
    SampleLab,
    SampleStatus,
)

_SAMPLE_STATUS_CODES = (
    SAMPLE_PENDING,
    SAMPLE_REGISTERED,
    SAMPLE_IN_PROGRESS,
    SAMPLE_ANALYZED,
    SAMPLE_COMPLETED,
    SAMPLE_REJECTED,
)

_DIRECTION_STATUS_ORDER = {
    code: index
    for index, code in enumerate(
        (
            DIRECTION_DRAFT,
            DIRECTION_REGISTERED,
            DIRECTION_IN_PROGRESS,
            DIRECTION_PARTIALLY_COMPLETED,
            DIRECTION_COMPLETED,
        )
    )
}

_SAMPLE_STATUS_ORDER = {
    code: index
    for index, code in enumerate(
        (
            SAMPLE_PENDING,
            SAMPLE_REGISTERED,
            SAMPLE_IN_PROGRESS,
            SAMPLE_ANALYZED,
            SAMPLE_COMPLETED,
            SAMPLE_REJECTED,
        )
    )
}


def _sorted_by_lifecycle(rows: list[StatusCount], order: dict[str, int]) -> list[StatusCount]:
    # Unknown/legacy codes sort after the canonical pipeline, then by code.
    return sorted(rows, key=lambda row: (order.get(row.code or "", len(order)), row.code or ""))


class SqlAlchemyDashboardRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def summary(
        self,
        *,
        date_from: date,
        date_to: date,
        period: str,
    ) -> dict[str, object]:
        current = await self._current()
        timeline = await self._timeline(date_from=date_from, date_to=date_to, period=period)
        samples_by_status = await self._samples_by_status()
        research_by_lab = await self._research_by_lab()
        sample_types = await self._sample_types(date_from=date_from, date_to=date_to)

        return {
            "period": period,
            "date_from": date_from,
            "date_to": date_to,
            "updated_at": current.get("refreshed_at"),
            "kpis": _kpis(current),
            "timeline": timeline,
            "samples_by_status": samples_by_status,
            "research_by_lab": research_by_lab,
            "sample_types": sample_types,
        }

    async def _current(self) -> dict[str, Any]:
        result = await self.session.execute(
            text(
                """
                SELECT
                    refreshed_at,
                    directions_total,
                    directions_urgent_open,
                    samples_total,
                    samples_received_total,
                    samples_completed_total,
                    samples_rejected_total,
                    samples_open_total,
                    samples_overdue_open,
                    samples_urgent_open,
                    research_active_total,
                    tests_queued_total,
                    tests_in_progress_total,
                    tests_completed_total,
                    protocols_issued_total,
                    avg_sample_turnaround_minutes
                FROM dashboard_workflow_current
                LIMIT 1
                """
            )
        )
        row = result.mappings().first()
        return dict(row or {})

    async def _timeline(
        self,
        *,
        date_from: date,
        date_to: date,
        period: str,
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                """
                SELECT
                    date_trunc(:period, bucket_date::timestamp)::date AS bucket_start,
                    COALESCE(sum(directions_received), 0)::int AS directions_received,
                    COALESCE(sum(samples_received), 0)::int AS samples_received,
                    COALESCE(sum(samples_completed), 0)::int AS samples_completed,
                    COALESCE(sum(samples_rejected), 0)::int AS samples_rejected,
                    COALESCE(sum(research_completed), 0)::int AS research_completed,
                    COALESCE(sum(tests_completed), 0)::int AS tests_completed,
                    COALESCE(sum(tests_rejected), 0)::int AS tests_rejected,
                    COALESCE(sum(protocols_issued), 0)::int AS protocols_issued
                FROM dashboard_workflow_daily
                WHERE bucket_date BETWEEN :date_from AND :date_to
                GROUP BY bucket_start
                ORDER BY bucket_start
                """
            ),
            {"period": _postgres_period(period), "date_from": date_from, "date_to": date_to},
        )
        return [dict(row) for row in result.mappings().all()]

    async def _samples_by_status(self) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                """
                SELECT status_code, status_color, count
                FROM dashboard_samples_by_status
                ORDER BY count DESC, status_code
                """
            )
        )
        return [dict(row) for row in result.mappings().all()]

    async def _research_by_lab(self) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                """
                SELECT lab_id, lab_name, active_count, completed_count
                FROM dashboard_research_by_lab
                ORDER BY active_count DESC, completed_count DESC, lab_name
                LIMIT 12
                """
            )
        )
        return [dict(row) for row in result.mappings().all()]

    async def _sample_types(
        self,
        *,
        date_from: date,
        date_to: date,
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                """
                SELECT
                    sample_type_id,
                    sample_type_name,
                    COALESCE(sum(count), 0)::int AS count
                FROM dashboard_sample_type_daily
                WHERE bucket_date BETWEEN :date_from AND :date_to
                GROUP BY sample_type_id, sample_type_name
                ORDER BY count DESC, sample_type_name
                LIMIT 10
                """
            ),
            {"date_from": date_from, "date_to": date_to},
        )
        return [dict(row) for row in result.mappings().all()]


class SqlAlchemyRegistrarDashboardRepository:
    """Registrar dashboard read model — direct queries over base tables
    (`directions`, `samples`, and their status lookups). No materialized view is
    needed: the counts-by-status and recent-items reads are cheap and backed by
    existing `status_id` / `is_urgent` / partial `created_at DESC` indexes.
    """

    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def directions_by_status(self) -> list[StatusCount]:
        result = await self.session.execute(
            select(
                DirectionStatus.id,
                DirectionStatus.code,
                DirectionStatus.color,
                func.count(Direction.id),
            )
            .select_from(DirectionStatus)
            .outerjoin(
                Direction,
                and_(
                    Direction.status_id == DirectionStatus.id,
                    Direction.deleted_at.is_(None),
                ),
            )
            .where(DirectionStatus.deleted_at.is_(None))
            .group_by(
                DirectionStatus.id,
                DirectionStatus.code,
                DirectionStatus.color,
            )
        )
        rows = [
            StatusCount(id=status_id, code=code, color=color, count=count)
            for status_id, code, color, count in result.all()
        ]
        return _sorted_by_lifecycle(rows, _DIRECTION_STATUS_ORDER)

    async def samples_by_status(self) -> list[StatusCount]:
        result = await self.session.execute(
            select(
                SampleStatus.id,
                SampleStatus.code,
                SampleStatus.color,
                func.count(Sample.id),
            )
            .select_from(SampleStatus)
            .outerjoin(
                Sample,
                and_(
                    Sample.status_id == SampleStatus.id,
                    Sample.deleted_at.is_(None),
                ),
            )
            .where(SampleStatus.deleted_at.is_(None))
            .group_by(
                SampleStatus.id,
                SampleStatus.code,
                SampleStatus.color,
            )
        )
        rows = [
            StatusCount(id=status_id, code=code, color=color, count=count)
            for status_id, code, color, count in result.all()
        ]
        return _sorted_by_lifecycle(rows, _SAMPLE_STATUS_ORDER)

    async def urgent_open_total(self) -> int:
        directions = await self.session.scalar(
            select(func.count())
            .select_from(Direction)
            .where(
                Direction.is_urgent.is_(True),
                Direction.is_done.is_(False),
                Direction.deleted_at.is_(None),
            )
        )
        samples = await self.session.scalar(
            select(func.count())
            .select_from(Sample)
            .where(
                Sample.is_urgent.is_(True),
                Sample.is_done.is_(False),
                Sample.deleted_at.is_(None),
            )
        )
        return int(directions or 0) + int(samples or 0)

    async def samples_by_lab(self) -> list[LabStatusCount]:
        # Live samples per lab (via the sample_labs assignment) broken down by
        # current status — the two levels of the nested donut. A sample assigned
        # to several labs is counted under each.
        result = await self.session.execute(
            select(
                Lab.id.label("lab_id"),
                Lab.code.label("lab_code"),
                Lab.name.label("lab_name"),
                SampleStatus.code.label("status_code"),
                SampleStatus.color.label("status_color"),
                func.count(Sample.id).label("cnt"),
            )
            .select_from(SampleLab)
            .join(
                Sample,
                and_(Sample.id == SampleLab.sample_id, Sample.deleted_at.is_(None)),
            )
            .join(Lab, Lab.id == SampleLab.lab_id)
            .outerjoin(SampleStatus, SampleStatus.id == Sample.status_id)
            .where(SampleLab.deleted_at.is_(None))
            .group_by(
                Lab.id,
                Lab.code,
                Lab.name,
                SampleStatus.code,
                SampleStatus.color,
            )
        )
        rows = [
            LabStatusCount(
                lab_id=row.lab_id,
                lab_code=row.lab_code,
                lab_name=row.lab_name,
                status_code=row.status_code,
                status_color=row.status_color,
                count=row.cnt,
            )
            for row in result.all()
        ]
        return sorted(
            rows,
            key=lambda r: (
                r.lab_name,
                _SAMPLE_STATUS_ORDER.get(r.status_code or "", len(_SAMPLE_STATUS_ORDER)),
            ),
        )

    async def directions_received_between(self, *, start: datetime, end: datetime) -> int:
        count = await self.session.scalar(
            select(func.count())
            .select_from(Direction)
            .where(
                Direction.received_at >= start,
                Direction.received_at < end,
                Direction.deleted_at.is_(None),
            )
        )
        return int(count or 0)

    async def samples_received_between(self, *, start: datetime, end: datetime) -> int:
        count = await self.session.scalar(
            select(func.count())
            .select_from(Sample)
            .where(
                Sample.received_at >= start,
                Sample.received_at < end,
                Sample.deleted_at.is_(None),
            )
        )
        return int(count or 0)

    async def recent_directions(self, *, limit: int) -> list[RecentDirection]:
        # Most recently received directions (org-wide) — created_by is a technical
        # field, so recency is measured by received_at, not who keyed it in.
        result = await self.session.execute(
            select(
                Direction.id,
                Direction.year_no,
                Direction.base_no,
                Direction.is_urgent,
                Direction.received_at,
                DirectionStatus.code.label("status_code"),
                DirectionStatus.color.label("status_color"),
            )
            .outerjoin(DirectionStatus, Direction.status_id == DirectionStatus.id)
            .where(
                Direction.received_at.is_not(None),
                Direction.deleted_at.is_(None),
            )
            .order_by(Direction.received_at.desc())
            .limit(limit)
        )
        return [
            RecentDirection(
                id=row.id,
                year_no=row.year_no,
                base_no=row.base_no,
                is_urgent=row.is_urgent,
                received_at=row.received_at,
                status_code=row.status_code,
                status_color=row.status_color,
            )
            for row in result.all()
        ]

    async def timeline(
        self,
        *,
        date_from: date,
        date_to: date,
        period: str,
    ) -> list[TimelineBucket]:
        # Sample intake bucketed by received_at (created_at is technical). Each
        # bucket carries a per-status breakdown of the samples received in it, so
        # the whole lifecycle (including defects) is visible over time. One FILTER
        # column per sample status is pivoted into the by_status dict below.
        # generate_series fills empty buckets so the chart has no gaps; date_to is
        # inclusive, hence the exclusive upper bound of the day after it.
        status_columns = ",\n".join(
            f"count(*) FILTER (WHERE ss.code = :code_{code}) AS {code}"
            for code in _SAMPLE_STATUS_CODES
        )
        select_columns = ",\n".join(
            f"CAST(COALESCE(s.{code}, 0) AS int) AS {code}" for code in _SAMPLE_STATUS_CODES
        )
        result = await self.session.execute(
            text(
                f"""
                WITH buckets AS (
                    SELECT generate_series(
                        date_trunc(:period, CAST(:date_from AS timestamptz)),
                        date_trunc(:period, CAST(:date_to AS timestamptz)),
                        CAST('1 ' || :period AS interval)
                    ) AS bucket
                ),
                samples AS (
                    SELECT
                        date_trunc(:period, s.received_at) AS bucket,
                        {status_columns}
                    FROM samples s
                    LEFT JOIN sample_statuses ss ON ss.id = s.status_id
                    WHERE s.deleted_at IS NULL
                      AND s.received_at >= CAST(:date_from AS timestamptz)
                      AND s.received_at < (CAST(:date_to AS date) + 1)
                    GROUP BY 1
                )
                SELECT
                    CAST(b.bucket AS date) AS bucket_start,
                    {select_columns}
                FROM buckets b
                LEFT JOIN samples s ON s.bucket = b.bucket
                ORDER BY b.bucket
                """
            ),
            {
                "period": _postgres_period(period),
                "date_from": date_from,
                "date_to": date_to,
                **{f"code_{code}": code for code in _SAMPLE_STATUS_CODES},
            },
        )
        return [
            TimelineBucket(
                bucket_start=row["bucket_start"],
                by_status={code: row[code] for code in _SAMPLE_STATUS_CODES},
            )
            for row in result.mappings().all()
        ]


def _int(row: dict[str, Any], key: str) -> int:
    value = row.get(key)
    return int(value or 0)


def _postgres_period(period: str) -> str:
    return {
        "daily": "day",
        "weekly": "week",
        "monthly": "month",
    }[period]


def _kpis(row: dict[str, Any]) -> list[dict[str, object]]:
    return [
        {
            "key": "samples_received",
            "label": "Поступило образцов",
            "value": _int(row, "samples_received_total"),
            "unit": "count",
            "icon": "i-lucide-package-check",
        },
        {
            "key": "tests_completed",
            "label": "Выполнено тестов",
            "value": _int(row, "tests_completed_total"),
            "unit": "count",
            "icon": "i-lucide-flask-conical",
        },
        {
            "key": "samples_overdue",
            "label": "Просрочено",
            "value": _int(row, "samples_overdue_open"),
            "unit": "count",
            "icon": "i-lucide-clock-alert",
        },
        {
            "key": "avg_turnaround_minutes",
            "label": "Среднее время",
            "value": _int(row, "avg_sample_turnaround_minutes"),
            "unit": "minutes",
            "icon": "i-lucide-timer",
        },
        {
            "key": "samples_rejected",
            "label": "Брак",
            "value": _int(row, "samples_rejected_total"),
            "unit": "count",
            "icon": "i-lucide-triangle-alert",
        },
        {
            "key": "research_active",
            "label": "Исследования в работе",
            "value": _int(row, "research_active_total"),
            "unit": "count",
            "icon": "i-lucide-activity",
        },
    ]
