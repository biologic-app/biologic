from uuid import UUID

import pytest
from pydantic import ValidationError

from src.contexts.laboratory_workflow.application.dto import CommandResult, RegisterSampleInput


def test_command_result_is_minimal_primary_entity_projection() -> None:
    result = CommandResult.model_validate(
        {
            "id": UUID("00000000-0000-0000-0000-000000000001"),
            "status_id": UUID("00000000-0000-0000-0000-000000000002"),
            "updated_at": "2026-05-14T10:00:00Z",
        }
    )

    assert result.model_dump(mode="json") == {
        "id": "00000000-0000-0000-0000-000000000001",
        "status_id": "00000000-0000-0000-0000-000000000002",
        "updated_at": "2026-05-14T10:00:00Z",
    }


def test_register_sample_input_parses_timezone_aware_timestamps() -> None:
    command = RegisterSampleInput.model_validate(
        {
            "sample_id": UUID("00000000-0000-0000-0000-000000000001"),
            "actor_id": UUID("00000000-0000-0000-0000-000000000003"),
            "received_at": "2026-05-14T10:00:00Z",
            "deadline": "2026-05-15T10:00:00+03:00",
        }
    )

    assert command.received_at.tzinfo is not None
    assert command.deadline is not None
    assert command.deadline.tzinfo is not None


@pytest.mark.parametrize("received_at", ["not-a-date", "2026-05-14T10:00:00"])
def test_register_sample_input_rejects_invalid_or_naive_timestamp(received_at: str) -> None:
    with pytest.raises(ValidationError):
        RegisterSampleInput.model_validate(
            {
                "sample_id": UUID("00000000-0000-0000-0000-000000000001"),
                "actor_id": UUID("00000000-0000-0000-0000-000000000003"),
                "received_at": received_at,
            }
        )
