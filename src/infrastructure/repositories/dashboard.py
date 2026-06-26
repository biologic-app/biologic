from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


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
                SELECT status_code, status_name, count
                FROM dashboard_samples_by_status
                ORDER BY count DESC, status_name
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
