from datetime import UTC, datetime
from uuid import UUID

from src.core.cursor_pagination import decode_cursor, encode_cursor


def test_cursor_round_trip_preserves_sort_context() -> None:
    cursor = encode_cursor(
        sort_by="created_at",
        sort_order="desc",
        sort_value=datetime(2026, 5, 25, 10, 0, tzinfo=UTC),
        item_id=UUID("00000000-0000-0000-0000-000000000001"),
    )

    decoded = decode_cursor(cursor)

    assert decoded.sort_by == "created_at"
    assert decoded.sort_order == "desc"
    assert decoded.sort_value == "2026-05-25T10:00:00Z"
    assert decoded.item_id == UUID("00000000-0000-0000-0000-000000000001")
