from datetime import UTC, datetime
from uuid import UUID

from src.infrastructure.repositories.released_samples import _build_groups

COMPLETED = "completed"

DIR_ALL = UUID("00000000-0000-0000-0000-0000000000a1")
DIR_MIX = UUID("00000000-0000-0000-0000-0000000000a2")
DIR_NONE = UUID("00000000-0000-0000-0000-0000000000a3")


def _row(
    *,
    direction_id: UUID,
    sample_id: str,
    status_code: str,
    completed_at: datetime | None = None,
    protocol_id: UUID | None = None,
    year_no: int = 2026,
    base_no: int = 1,
) -> dict[str, object]:
    return {
        "direction_id": direction_id,
        "year_no": year_no,
        "base_no": base_no,
        "doctor_name": "Иванов Иван",
        "object_name": "Ферма №1",
        "object_code": "F1",
        "sample_id": UUID(sample_id),
        "sample_name": f"Проба {sample_id[-1]}",
        "status_code": status_code,
        "status_name": status_code.title(),
        "sample_type_name": "Молоко",
        "protocol_id": protocol_id,
        "completed_at": completed_at,
    }


def test_direction_with_all_samples_completed_is_flagged_released() -> None:
    rows = [
        _row(
            direction_id=DIR_ALL,
            sample_id="00000000-0000-0000-0000-000000000b01",
            status_code=COMPLETED,
            completed_at=datetime(2026, 7, 10, tzinfo=UTC),
            base_no=10,
        ),
        _row(
            direction_id=DIR_ALL,
            sample_id="00000000-0000-0000-0000-000000000b02",
            status_code=COMPLETED,
            completed_at=datetime(2026, 7, 11, tzinfo=UTC),
            base_no=10,
        ),
    ]

    groups = _build_groups(rows, completed_code=COMPLETED)

    assert len(groups) == 1
    group = groups[0]
    assert group["direction"]["id"] == DIR_ALL
    assert group["direction"]["doctor"] == "Иванов Иван"
    assert group["direction"]["object"] == {"name": "Ферма №1", "code": "F1"}
    assert group["released_count"] == 2
    assert group["total_count"] == 2
    assert group["all_released"] is True
    assert "_latest_completed" not in group


def test_direction_with_mixed_samples_is_not_all_released() -> None:
    rows = [
        _row(
            direction_id=DIR_MIX,
            sample_id="00000000-0000-0000-0000-000000000c01",
            status_code=COMPLETED,
            completed_at=datetime(2026, 7, 12, tzinfo=UTC),
            base_no=20,
        ),
        _row(
            direction_id=DIR_MIX,
            sample_id="00000000-0000-0000-0000-000000000c02",
            status_code="in_progress",
            base_no=20,
        ),
        _row(
            direction_id=DIR_MIX,
            sample_id="00000000-0000-0000-0000-000000000c03",
            status_code="rejected",
            base_no=20,
        ),
    ]

    groups = _build_groups(rows, completed_code=COMPLETED)

    assert len(groups) == 1
    group = groups[0]
    assert group["released_count"] == 1
    assert group["total_count"] == 3
    assert group["all_released"] is False


def test_directions_without_released_samples_are_excluded() -> None:
    rows = [
        _row(
            direction_id=DIR_NONE,
            sample_id="00000000-0000-0000-0000-000000000d01",
            status_code="in_progress",
            base_no=30,
        ),
        _row(
            direction_id=DIR_NONE,
            sample_id="00000000-0000-0000-0000-000000000d02",
            status_code="analyzed",
            base_no=30,
        ),
    ]

    groups = _build_groups(rows, completed_code=COMPLETED)

    assert groups == []


def test_groups_are_ordered_by_most_recent_completed_first() -> None:
    rows = [
        _row(
            direction_id=DIR_MIX,
            sample_id="00000000-0000-0000-0000-000000000c01",
            status_code=COMPLETED,
            completed_at=datetime(2026, 7, 1, tzinfo=UTC),
            base_no=20,
        ),
        _row(
            direction_id=DIR_ALL,
            sample_id="00000000-0000-0000-0000-000000000b01",
            status_code=COMPLETED,
            completed_at=datetime(2026, 7, 15, tzinfo=UTC),
            base_no=10,
        ),
    ]

    groups = _build_groups(rows, completed_code=COMPLETED)

    assert [group["direction"]["id"] for group in groups] == [DIR_ALL, DIR_MIX]
