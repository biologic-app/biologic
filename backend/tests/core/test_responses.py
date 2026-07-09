from uuid import UUID

import pytest
from pydantic import ValidationError

from src.core.pagination import PageMeta, PaginationParams
from src.core.responses import ListResponse, ResponseMeta, SingleResponse


def test_pagination_params_defaults_and_limit_cap() -> None:
    params = PaginationParams()

    assert params.limit == 50
    assert params.cursor is None

    capped = PaginationParams(limit=500)
    assert capped.limit == 100


def test_pagination_params_accepts_cursor() -> None:
    params = PaginationParams(cursor="opaque-cursor")

    assert params.cursor == "opaque-cursor"


def test_pagination_params_accepts_search() -> None:
    params = PaginationParams(search="Сыворотка")

    assert params.search == "Сыворотка"


def test_pagination_params_rejects_offset() -> None:
    with pytest.raises(ValidationError) as exc_info:
        PaginationParams.model_validate({"offset": 0})

    assert "extra_forbidden" in str(exc_info.value)


def test_single_response_uses_snake_case_meta() -> None:
    response = SingleResponse[dict[str, str]](
        data={"id": "abc"},
        meta=ResponseMeta(request_id=UUID("00000000-0000-0000-0000-000000000001")),
    )

    payload = response.model_dump(mode="json")

    assert payload["data"] == {"id": "abc"}
    assert payload["meta"]["version"] == "v1"
    assert payload["meta"]["request_id"] == "00000000-0000-0000-0000-000000000001"


def test_list_response_meta_contains_include_fields() -> None:
    response = ListResponse[dict[str, str]](
        items=[{"id": "abc"}],
        meta=PageMeta(
            total=1,
            limit=50,
            has_more=False,
            includes_requested=["status"],
            includes_applied=["status"],
            includes_allowed=["status", "lab"],
        ),
    )

    payload = response.model_dump(mode="json")

    assert payload["items"] == [{"id": "abc"}]
    assert "offset" not in payload["meta"]
    assert payload["meta"]["includes_requested"] == ["status"]
    assert payload["meta"]["includes_allowed"] == ["status", "lab"]


def test_list_response_meta_defaults_timestamp_and_serializes_request_id() -> None:
    response = ListResponse[dict[str, str]](
        items=[],
        meta=PageMeta(
            request_id=UUID("00000000-0000-0000-0000-000000000002"),
            total=0,
            limit=50,
            has_more=False,
        ),
    )

    payload = response.model_dump(mode="json")

    assert payload["meta"]["timestamp"].endswith("Z")
    assert payload["meta"]["request_id"] == "00000000-0000-0000-0000-000000000002"
