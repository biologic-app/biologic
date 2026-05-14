from uuid import UUID

from src.contexts.laboratory_workflow.application.dto import CommandResult


def test_command_result_is_minimal_primary_entity_projection() -> None:
    result = CommandResult(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        status_id=UUID("00000000-0000-0000-0000-000000000002"),
        updated_at="2026-05-14T10:00:00Z",
    )

    assert result.model_dump(mode="json") == {
        "id": "00000000-0000-0000-0000-000000000001",
        "status_id": "00000000-0000-0000-0000-000000000002",
        "updated_at": "2026-05-14T10:00:00Z",
    }
