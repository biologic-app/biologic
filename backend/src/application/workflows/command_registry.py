"""Registry mapping a workflow ``DomainAction.command`` to a laboratory_workflow
mutation, composed through the shared Unit of Work so execute-step stays atomic.

The registry adds no domain logic: it only resolves arguments and delegates to
the existing ``uow.workflow`` command methods (which flush, never commit).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.contexts.laboratory_workflow.application.dto import CommandResult
from src.core.errors import BadRequestError
from src.core.status_codes import TEST_COMPLETED, TEST_REJECTED
from src.domain.uow import UnitOfWork

Mutator = Callable[
    [UnitOfWork, UUID, dict[str, Any], UUID, UUID],
    Awaitable[CommandResult],
]


@dataclass(frozen=True)
class CommandDefinition:
    resource: str          # status_policy resource key, for the transition pre-check
    to_code: str           # target status code the command transitions into
    target_key: str        # key in resolved_args holding the target entity id
    mutate: Mutator


async def _tests_complete(
    uow: UnitOfWork,
    target_id: UUID,
    args: dict[str, Any],
    actor_id: UUID,
    run_id: UUID,
) -> CommandResult:
    return await uow.workflow.complete_test(
        test_id=target_id,
        actor_id=actor_id,
        value=_as_str(_first(args, "result", "value")),
        norm=_opt_str(args.get("norm")),
        comment=_opt_str(_first(args, "comment", "reason")),
        verdict=_coerce_verdict(args.get("verdict")),
        workflow_run_id=run_id,
    )


async def _tests_reject(
    uow: UnitOfWork,
    target_id: UUID,
    args: dict[str, Any],
    actor_id: UUID,
    run_id: UUID,
) -> CommandResult:
    return await uow.workflow.reject_test(
        test_id=target_id,
        actor_id=actor_id,
        reason=_as_str(_first(args, "reason", "comment")),
        workflow_run_id=run_id,
    )


COMMAND_REGISTRY: dict[str, CommandDefinition] = {
    "tests.complete": CommandDefinition("tests", TEST_COMPLETED, "test_id", _tests_complete),
    "tests.reject": CommandDefinition("tests", TEST_REJECTED, "test_id", _tests_reject),
}


def resolve_target_id(definition: CommandDefinition, args: dict[str, Any]) -> UUID:
    raw = args.get(definition.target_key)
    if raw is None:
        raise BadRequestError(
            f"Action is missing target field {definition.target_key!r} in resolved_args."
        )
    return _coerce_uuid(raw, definition.target_key)


def _coerce_uuid(value: Any, label: str) -> UUID:
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, TypeError) as exc:
        raise BadRequestError(f"Value for {label!r} is not a valid id: {value!r}.") from exc


def _first(args: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in args and args[key] is not None:
            return args[key]
    return None


def _as_str(value: Any) -> str:
    return "" if value is None else str(value)


def _opt_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _coerce_verdict(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"pass", "true", "yes", "1", "ok"}:
        return True
    if text in {"fail", "false", "no", "0"}:
        return False
    return None
