from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.status_codes import SAMPLE_COMPLETED

# Ordering floor for directions whose released samples carry no completed_at.
_EPOCH = datetime.min.replace(tzinfo=UTC)


class SqlAlchemyReleasedSamplesRepository:
    """Read-projection: directions that have at least one released
    (``completed``) sample, with the full sample roster of each direction."""

    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def released_by_direction(self) -> list[dict[str, Any]]:
        rows = await self._rows()
        return _build_groups(rows, completed_code=SAMPLE_COMPLETED)

    async def _rows(self) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                """
                SELECT
                    d.id AS direction_id,
                    d.year_no AS year_no,
                    d.base_no AS base_no,
                    NULLIF(
                        TRIM(CONCAT_WS(' ', doc.last_name, doc.first_name, doc.patronymic)),
                        ''
                    ) AS doctor_name,
                    obj.name AS object_name,
                    obj.code AS object_code,
                    s.id AS sample_id,
                    s.name AS sample_name,
                    ss.code AS status_code,
                    ss.name AS status_name,
                    st.name AS sample_type_name,
                    s.protocol_id AS protocol_id,
                    s.completed_at AS completed_at
                FROM samples s
                JOIN directions d
                    ON d.id = s.direction_id AND d.deleted_at IS NULL
                LEFT JOIN doctors doc ON doc.id = d.doctor_id
                LEFT JOIN objects obj ON obj.id = d.object_id
                LEFT JOIN sample_types st ON st.id = s.sample_type_id
                LEFT JOIN sample_statuses ss ON ss.id = s.status_id
                WHERE s.deleted_at IS NULL
                  AND EXISTS (
                      SELECT 1
                      FROM samples cs
                      JOIN sample_statuses css ON css.id = cs.status_id
                      WHERE cs.direction_id = d.id
                        AND cs.deleted_at IS NULL
                        AND css.code = :completed_code
                  )
                ORDER BY d.year_no, d.base_no, s.created_at, s.id
                """
            ),
            {"completed_code": SAMPLE_COMPLETED},
        )
        return [dict(row) for row in result.mappings().all()]


def _build_groups(
    rows: list[dict[str, Any]],
    *,
    completed_code: str,
) -> list[dict[str, Any]]:
    """Group flat sample rows by direction, compute release counts and the
    ``all_released`` flag, drop directions without a single released sample, and
    order the survivors by most recently completed sample first.

    Pure function so it can be unit-tested with synthetic rows.
    """

    groups: dict[Any, dict[str, Any]] = {}
    order: list[Any] = []

    for row in rows:
        direction_id = row["direction_id"]
        group = groups.get(direction_id)
        if group is None:
            group = {
                "direction": {
                    "id": direction_id,
                    "year_no": row.get("year_no"),
                    "base_no": row.get("base_no"),
                    "doctor": row.get("doctor_name"),
                    "object": {
                        "name": row.get("object_name"),
                        "code": row.get("object_code"),
                    },
                },
                "samples": [],
                "released_count": 0,
                "total_count": 0,
                "all_released": False,
                "_latest_completed": None,
            }
            groups[direction_id] = group
            order.append(direction_id)

        group["samples"].append(
            {
                "id": row["sample_id"],
                "name": row.get("sample_name"),
                "status_code": row.get("status_code"),
                "status_name": row.get("status_name"),
                "sample_type_name": row.get("sample_type_name"),
                "protocol_id": row.get("protocol_id"),
                "completed_at": row.get("completed_at"),
            }
        )
        group["total_count"] += 1
        if row.get("status_code") == completed_code:
            group["released_count"] += 1
            completed_at = row.get("completed_at")
            if completed_at is not None and (
                group["_latest_completed"] is None
                or completed_at > group["_latest_completed"]
            ):
                group["_latest_completed"] = completed_at

    result: list[dict[str, Any]] = []
    for direction_id in order:
        group = groups[direction_id]
        if group["released_count"] == 0:
            continue
        group["all_released"] = (
            group["total_count"] > 0 and group["released_count"] == group["total_count"]
        )
        result.append(group)

    result.sort(key=lambda group: group["_latest_completed"] or _EPOCH, reverse=True)
    for group in result:
        group.pop("_latest_completed", None)
    return result
