"""Minimal in-process publisher/subscriber (Observer) bus for domain events.

Framework- and context-agnostic on purpose: `core/` must never import from
`contexts/` (enforced by `test_core_does_not_import_contexts`), so this only
knows about a generic event shape, never about workflow/notification types
specifically. Contexts wire their own subscribers onto an instance of
`EventPublisher` per unit of work.

No persistence, no retry, no async dispatch queue: every subscriber runs
in-process, in registration order, inside the same DB transaction as the
command that raised the event. That matches how this backend actually
works today — one Unit of Work, one commit per command — so anything
heavier (a message broker, an outbox table) would be solving a problem
this deployment doesn't have.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from typing import Any, Protocol

EventHandler = Callable[[Any], Awaitable[None]]


class Event(Protocol):
    """Structural shape every published event must satisfy.

    Declared as read-only properties (not plain attributes) so frozen
    dataclasses like StatusChanged — which expose these as read-only
    fields — satisfy the protocol structurally.
    """

    @property
    def entity_type(self) -> str: ...

    @property
    def entity_id(self) -> Any: ...

    @property
    def event_type(self) -> str: ...


class EventPublisher:
    """Publisher side of the pattern: subscribers register interest, then
    every published event is delivered to each of them in turn."""

    def __init__(self) -> None:
        self._subscribers: list[EventHandler] = []

    def subscribe(self, handler: EventHandler) -> None:
        self._subscribers.append(handler)

    async def publish(self, event: Event) -> None:
        for handler in self._subscribers:
            await handler(event)

    async def publish_all(self, events: Iterable[Event]) -> None:
        for event in events:
            await self.publish(event)
