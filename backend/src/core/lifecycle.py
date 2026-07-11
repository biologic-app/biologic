"""Graceful shutdown coordination for long-lived responses (SSE).

uvicorn tears open connections down *before* it fires the ASGI lifespan
``shutdown`` event: ``Server.shutdown`` first calls ``connection.shutdown()``
(which only flips ``keep_alive`` off for an in-flight response), then waits in
``_wait_tasks_to_complete`` up to ``timeout_graceful_shutdown`` and *only then*
runs ``lifespan.shutdown``. An SSE endpoint that polls in an endless loop
therefore keeps the event loop alive until that timeout forcibly cancels it —
so a lifespan-level flag would be noticed far too late.

To stop those streams cleanly and promptly we publish a process-wide
``asyncio.Event`` on ``app.state.shutdown_event``. A signal bridge sets it the
instant SIGINT/SIGTERM arrives — chaining, not replacing, uvicorn's own handler
— so every stream notices immediately, finishes its current response and lets
the process exit. The lifespan also sets it on normal ASGI shutdown, so stops
that never raise a signal (embedded runs, ``--reload``, tests) behave the same.
"""

from __future__ import annotations

import asyncio
import signal
import threading
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from types import FrameType

from fastapi import FastAPI

_SHUTDOWN_SIGNALS: tuple[signal.Signals, ...] = (signal.SIGINT, signal.SIGTERM)


def new_shutdown_event() -> asyncio.Event:
    """Create the shutdown flag shared between the lifespan and SSE streams.

    Constructed at app-build time (no running loop yet); an ``asyncio.Event``
    binds to a loop lazily on first ``wait()``/``set()``, so this is safe.
    """
    return asyncio.Event()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    shutdown_event = getattr(app.state, "shutdown_event", None)
    if shutdown_event is None:
        shutdown_event = new_shutdown_event()
        app.state.shutdown_event = shutdown_event

    restore = _bridge_signals_to(shutdown_event)
    try:
        yield
    finally:
        # Covers stops that never raise a signal (ASGI stop, --reload, tests)
        # and is a harmless no-op when the signal bridge already fired.
        shutdown_event.set()
        restore()


def _bridge_signals_to(event: asyncio.Event) -> Callable[[], None]:
    """Set ``event`` on SIGINT/SIGTERM while still invoking uvicorn's handler.

    Returns a callable that restores the previously installed handlers. Falls
    back to a no-op restorer when signals are unavailable here (e.g. off the
    main thread, as under ``httpx.ASGITransport`` in tests).
    """
    if threading.current_thread() is not threading.main_thread():
        return lambda: None

    loop = asyncio.get_running_loop()
    previous: dict[signal.Signals, Callable[..., object] | int | None] = {}

    def _handle(signum: int, frame: FrameType | None) -> None:
        # Wake the loop safely from signal context, then defer to uvicorn so
        # its own ``should_exit`` shutdown sequence still runs.
        loop.call_soon_threadsafe(event.set)
        chained = previous.get(signal.Signals(signum))
        if callable(chained):
            chained(signum, frame)

    for sig in _SHUTDOWN_SIGNALS:
        try:
            previous[sig] = signal.signal(sig, _handle)
        except (ValueError, OSError):
            # Signal not supported in this context; leave any existing handler.
            previous.pop(sig, None)

    def _restore() -> None:
        for sig, handler in previous.items():
            try:
                signal.signal(sig, handler if handler is not None else signal.SIG_DFL)
            except (ValueError, OSError):
                pass

    return _restore
