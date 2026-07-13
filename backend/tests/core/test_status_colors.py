from src.application.catalogs.use_cases._shared import serialize
from src.application.catalogs.use_cases.direction_status_crud import (
    _FIELDS as DIRECTION_STATUS_FIELDS,
)
from src.application.catalogs.use_cases.research_status_crud import (
    _FIELDS as RESEARCH_STATUS_FIELDS,
)
from src.application.catalogs.use_cases.sample_status_crud import (
    _FIELDS as SAMPLE_STATUS_FIELDS,
)
from src.application.catalogs.use_cases.test_status_crud import (
    _FIELDS as TEST_STATUS_FIELDS,
)
from src.core.status_colors import (
    ALLOWED_STATUS_COLORS,
    DIRECTION_STATUS_COLORS,
    RESEARCH_STATUS_COLORS,
    SAMPLE_STATUS_COLORS,
    TEST_STATUS_COLORS,
)

_ALL_MAPS = (
    DIRECTION_STATUS_COLORS,
    SAMPLE_STATUS_COLORS,
    RESEARCH_STATUS_COLORS,
    TEST_STATUS_COLORS,
)


def test_allowed_vocabulary_is_the_fixed_eight() -> None:
    assert ALLOWED_STATUS_COLORS == frozenset(
        {"gray", "indigo", "blue", "violet", "lime", "green", "amber", "red"}
    )


def test_every_mapped_color_is_in_the_allowed_vocabulary() -> None:
    for mapping in _ALL_MAPS:
        for code, color in mapping.items():
            assert color in ALLOWED_STATUS_COLORS, (code, color)


def test_per_status_colors_match_the_specification() -> None:
    assert DIRECTION_STATUS_COLORS == {
        "draft": "gray",
        "registered": "indigo",
        "in_progress": "blue",
        "partially_completed": "lime",
        "completed": "green",
    }
    assert SAMPLE_STATUS_COLORS == {
        "pending": "amber",
        "registered": "indigo",
        "in_progress": "blue",
        "analyzed": "violet",
        "completed": "green",
        "rejected": "red",
    }
    assert RESEARCH_STATUS_COLORS == {
        "draft": "gray",
        "ordered": "amber",
        "in_progress": "blue",
        "completed": "green",
        "rejected": "red",
    }
    assert TEST_STATUS_COLORS == {
        "queued": "amber",
        "in_progress": "blue",
        "completed": "green",
        "rejected": "red",
    }


def test_sample_completed_is_green() -> None:
    assert SAMPLE_STATUS_COLORS["completed"] == "green"


def test_status_use_cases_expose_color_field() -> None:
    for fields in (
        DIRECTION_STATUS_FIELDS,
        SAMPLE_STATUS_FIELDS,
        RESEARCH_STATUS_FIELDS,
        TEST_STATUS_FIELDS,
    ):
        assert "color" in fields


def test_serializer_emits_color_from_status_field_set() -> None:
    class _Row:
        id = "00000000-0000-0000-0000-000000000001"
        code = "completed"
        name = "Закрыт"
        color = "green"
        created_at = None
        updated_at = None

    serialized = serialize(_Row(), SAMPLE_STATUS_FIELDS)

    assert serialized["color"] == "green"
    assert serialized["code"] == "completed"
