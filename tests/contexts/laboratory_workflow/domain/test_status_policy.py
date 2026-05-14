import pytest

from src.contexts.laboratory_workflow.domain.status_policy import (
    InvalidStatusTransition,
    ensure_allowed_transition,
)


def test_direction_register_transition_is_allowed() -> None:
    ensure_allowed_transition("directions", "draft", "registered")


def test_direction_patch_status_transition_is_not_allowed() -> None:
    with pytest.raises(InvalidStatusTransition) as exc:
        ensure_allowed_transition("directions", "draft", "completed")

    assert exc.value.code == "invalid_status_transition"


@pytest.mark.parametrize(
    ("resource", "from_code", "to_code"),
    [
        ("samples", "pending", "registered"),
        ("samples", "pending", "rejected"),
        ("samples", "analyzed", "completed"),
        ("research", "draft", "ordered"),
        ("research", "ordered", "in_progress"),
        ("research", "in_progress", "completed"),
        ("tests", "queued", "in_progress"),
        ("tests", "in_progress", "completed"),
        ("tests", "in_progress", "queued"),
    ],
)
def test_allowed_mvp_transitions(resource: str, from_code: str, to_code: str) -> None:
    ensure_allowed_transition(resource, from_code, to_code)
