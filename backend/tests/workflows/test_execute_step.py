from __future__ import annotations

from uuid import UUID

import pytest
from wf_fakes import FakeLabRepo, FakeWorkflowsRepo, FakeWorkflowsUoW, uow_factory

from src.application.workflows.dto import ExecuteStepInput, StepActionInput
from src.application.workflows.use_cases.execute_step import ExecuteStepUseCase
from src.core.errors import BadRequestError, DomainConflictError, NotFoundError

RUN_ID = UUID("00000000-0000-0000-0000-0000000000a1")
TEST_ID = UUID("00000000-0000-0000-0000-0000000000a2")
TEST_ID_2 = UUID("00000000-0000-0000-0000-0000000000a3")
ACTOR_ID = UUID("00000000-0000-0000-0000-0000000000a4")
NODE_ID = "n-result"


def _complete_action(action_id: str = "a1", test_id: UUID = TEST_ID) -> StepActionInput:
    return StepActionInput(
        action_id=action_id,
        command="tests.complete",
        resolved_args={
            "test_id": str(test_id),
            "actor_id": str(ACTOR_ID),
            "result": "5",
            "verdict": "pass",
        },
    )


def _input(*actions: StepActionInput, attempt: int = 1) -> ExecuteStepInput:
    return ExecuteStepInput(
        run_id=RUN_ID,
        node_id=NODE_ID,
        attempt=attempt,
        actions=list(actions) or [_complete_action()],
    )


@pytest.mark.asyncio
async def test_execute_step_applies_and_correlates_to_run() -> None:
    workflows = FakeWorkflowsRepo(status_by_resource={"tests": "in_progress"})
    lab = FakeLabRepo()
    uow = FakeWorkflowsUoW(workflows, lab)
    use_case = ExecuteStepUseCase(uow_factory=uow_factory(uow))

    response = await use_case.execute(_input())

    assert response.data["status"] == "applied"
    assert response.data["already_applied"] is False
    assert len(lab.complete_calls) == 1
    assert lab.complete_calls[0]["test_id"] == TEST_ID
    assert lab.complete_calls[0]["actor_id"] == ACTOR_ID
    assert lab.complete_calls[0]["verdict"] is True
    # Correlation: the run id is threaded into the domain mutation.
    assert lab.complete_calls[0]["workflow_run_id"] == RUN_ID
    assert uow.committed is True
    assert len(workflows.recorded_steps) == 1
    activity = [e for e in workflows.events if e.kind == "activity"]
    assert len(activity) == 1


@pytest.mark.asyncio
async def test_execute_step_replay_is_idempotent() -> None:
    workflows = FakeWorkflowsRepo(status_by_resource={"tests": "in_progress"})
    lab = FakeLabRepo()
    uow = FakeWorkflowsUoW(workflows, lab)
    use_case = ExecuteStepUseCase(uow_factory=uow_factory(uow))

    first = await use_case.execute(_input(attempt=7))
    second = await use_case.execute(_input(attempt=7))

    assert first.data["status"] == "applied"
    assert second.data["status"] == "already_applied"
    assert second.data["already_applied"] is True
    # The mutation ran exactly once despite the replay.
    assert len(lab.complete_calls) == 1
    assert len(workflows.recorded_steps) == 1
    assert second.data["results"] == first.data["results"]


@pytest.mark.asyncio
async def test_execute_step_is_atomic_on_second_action_failure() -> None:
    workflows = FakeWorkflowsRepo(status_by_resource={"tests": "in_progress"})
    lab = FakeLabRepo()
    lab.fail_on_complete_call = 2  # second action explodes mid-mutation
    uow = FakeWorkflowsUoW(workflows, lab)
    use_case = ExecuteStepUseCase(uow_factory=uow_factory(uow))

    with pytest.raises(RuntimeError):
        await use_case.execute(
            _input(_complete_action("a1", TEST_ID), _complete_action("a2", TEST_ID_2))
        )

    # No commit, no step recorded — the first action is rolled back with the rest.
    assert uow.committed is False
    assert uow.rolled_back is True
    assert workflows.recorded_steps == []


@pytest.mark.asyncio
async def test_execute_step_conflict_on_forbidden_transition() -> None:
    # Test already completed → tests: completed -> completed is not allowed.
    workflows = FakeWorkflowsRepo(status_by_resource={"tests": "completed"})
    lab = FakeLabRepo()
    uow = FakeWorkflowsUoW(workflows, lab)
    use_case = ExecuteStepUseCase(uow_factory=uow_factory(uow))

    with pytest.raises(DomainConflictError) as exc:
        await use_case.execute(_input())

    assert exc.value.status_code == 409
    # Pre-check blocks before any mutation.
    assert lab.complete_calls == []
    assert uow.committed is False


@pytest.mark.asyncio
async def test_execute_step_run_not_found() -> None:
    workflows = FakeWorkflowsRepo(run=None)
    uow = FakeWorkflowsUoW(workflows)
    use_case = ExecuteStepUseCase(uow_factory=uow_factory(uow))

    with pytest.raises(NotFoundError):
        await use_case.execute(_input())


@pytest.mark.asyncio
async def test_execute_step_unknown_command() -> None:
    workflows = FakeWorkflowsRepo(status_by_resource={"tests": "in_progress"})
    uow = FakeWorkflowsUoW(workflows)
    use_case = ExecuteStepUseCase(uow_factory=uow_factory(uow))

    action = StepActionInput(action_id="a1", command="nope.unknown", resolved_args={})
    with pytest.raises(BadRequestError):
        await use_case.execute(_input(action))
