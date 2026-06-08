from datetime import UTC, datetime
from uuid import UUID

from src.core.crud_query import _build_filter_predicate
from src.infrastructure.db.models import Research


def test_datetime_range_filter_coerces_date_strings_to_datetime_bounds() -> None:
    predicate = _build_filter_predicate(
        Research.received_at,
        ["2026-06-20", "2026-07-22"],
    )

    assert predicate is not None
    lower, upper = list(predicate.clauses)
    assert lower.right.value == datetime(2026, 6, 20, tzinfo=UTC)
    assert upper.right.value == datetime(2026, 7, 22, 23, 59, 59, 999999, tzinfo=UTC)


def test_uuid_filter_coerces_string_to_exact_uuid_comparison() -> None:
    sample_id = "00000000-0000-0000-0000-000000000002"

    predicate = _build_filter_predicate(Research.sample_id, sample_id)

    assert predicate is not None
    assert predicate.right.value == UUID(sample_id)
