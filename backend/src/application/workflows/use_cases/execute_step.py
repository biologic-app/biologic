from __future__ import annotations

from typing import Any
from uuid import UUID

from src.application.workflows.command_registry import (
    COMMAND_REGISTRY,
    CommandDefinition,
    resolve_target_id,
)
from src.application.workflows.dto import ExecuteStepInput, ExecuteStepResult
from src.contexts.laboratory_workflow.domain.status_policy import (
    InvalidStatusTransition,
    ensure_allowed_transition,
)
from src.core.cursor_pagination import json_value
from src.core.errors import BadRequestError, DomainConflictError, NotFoundError
from src.core.responses import ResponseMeta, SingleResponse
from src.domain.uow import UnitOfWork, UnitOfWorkFactory

_OPERATION = "workflows.execute_step"


class ExecuteStepUseCase:
    """Server-side execution of a step's domain actions.

    A single Unit of Work provides idempotency (``workflow_step_executions``
    guard), a fast transition pre-check, atomic multi-action mutation via the
    laboratory_workflow command methods, audit correlation and an activity
    event. Any failure rolls the whole step back.
    """

    def __init__(self, *, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, command: ExecuteStepInput) -> SingleResponse[dict[str, object]]:
        async with self._uow_factory() as uow:
            await uow.workflows.get_run(command.run_id)

            existing = await uow.workflows.find_step_execution(
                command.run_id,
                command.node_id,
                command.attempt,
            )
            if existing is not None:
                stored = existing.result if isinstance(existing.result, dict) else {}
                return _response(
                    ExecuteStepResult(
                        status="already_applied",
                        already_applied=True,
                        node_id=command.node_id,
                        attempt=command.attempt,
                        results=list(stored.get("results", [])),
                    )
                )

            planned = await self._plan(uow, command)

            results: list[dict[str, Any]] = []
            for action, definition, target_id, actor_id in planned:
                command_result = await definition.mutate(
                    uow,
                    target_id,
                    action.resolved_args,
                    actor_id,
                    command.run_id,
                )
                results.append(
                    {
                        "action_id": action.action_id,
                        "command": action.command,
                        "result": {
                            "id": str(command_result.id),
                            "status_id": str(command_result.status_id),
                            "updated_at": json_value(command_result.updated_at),
                        },
                    }
                )

            await uow.workflows.record_step_execution(
                run_id=command.run_id,
                node_id=command.node_id,
                attempt=command.attempt,
                status="applied",
                result={"results": results},
            )
            await uow.workflows.append_event(
                run_id=command.run_id,
                kind="activity",
                node_id=command.node_id,
                payload={
                    "attempt": command.attempt,
                    "actions": [action.action_id for action in command.actions],
                },
                author=command.author,
            )
            await uow.commit()

            return _response(
                ExecuteStepResult(
                    status="applied",
                    already_applied=False,
                    node_id=command.node_id,
                    attempt=command.attempt,
                    results=results,
                )
            )

    async def _plan(
        self,
        uow: UnitOfWork,
        command: ExecuteStepInput,
    ) -> list[tuple[Any, CommandDefinition, UUID, UUID]]:
        planned: list[tuple[Any, CommandDefinition, UUID, UUID]] = []
        for action in command.actions:
            definition = COMMAND_REGISTRY.get(action.command)
            if definition is None:
                raise BadRequestError(f"Unknown workflow command {action.command!r}.")
            target_id = resolve_target_id(definition, action.resolved_args)
            from_code = await uow.workflows.read_status_code(definition.resource, target_id)
            if from_code is None:
                raise NotFoundError(
                    f"{definition.resource} target {target_id} was not found."
                )
            _ensure_transition(definition.resource, from_code, definition.to_code)
            actor_id = _resolve_actor(action.resolved_args, command.actor_id)
            planned.append((action, definition, target_id, actor_id))
        return planned


def _ensure_transition(resource: str, from_code: str, to_code: str) -> None:
    try:
        ensure_allowed_transition(resource, from_code, to_code)
    except InvalidStatusTransition as exc:
        raise DomainConflictError(
            code=exc.code,
            detail=f"Invalid {resource} status transition {from_code} -> {to_code}.",
        ) from exc


def _resolve_actor(args: dict[str, Any], fallback: UUID | None) -> UUID:
    raw = args.get("actor_id", fallback)
    if raw is None:
        raise BadRequestError("Action requires an actor_id (from resolved_args or the caller).")
    if isinstance(raw, UUID):
        return raw
    try:
        return UUID(str(raw))
    except (ValueError, TypeError) as exc:
        raise BadRequestError(f"actor_id is not a valid id: {raw!r}.") from exc


def _response(result: ExecuteStepResult) -> SingleResponse[dict[str, object]]:
    data: dict[str, object] = {
        "status": result.status,
        "already_applied": result.already_applied,
        "node_id": result.node_id,
        "attempt": result.attempt,
        "results": result.results,
    }
    return SingleResponse(data=data, meta=ResponseMeta(operation=_OPERATION))
