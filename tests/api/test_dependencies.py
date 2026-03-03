from __future__ import annotations

import inspect

import pytest

from src.api import dependencies
from src.core.config import Settings

SERVICE_PROVIDERS = [
    func
    for _, func in inspect.getmembers(dependencies, inspect.isfunction)
    if func.__name__.startswith("get_") and func.__name__.endswith("_service")
]


def _provider_kwargs(provider: object) -> dict[str, object]:
    params = inspect.signature(provider).parameters
    kwargs: dict[str, object] = {}
    if "db_session" in params:
        kwargs["db_session"] = object()
    if "settings" in params:
        kwargs["settings"] = Settings(auth_mode="mock")
    return kwargs


@pytest.mark.parametrize("provider", SERVICE_PROVIDERS)
async def test_dependency_provider_returns_service(provider) -> None:
    provided = provider(**_provider_kwargs(provider))
    if inspect.isasyncgen(provided):
        service = await anext(provided)
        await provided.aclose()
    elif inspect.isawaitable(provided):
        service = await provided
    else:
        service = provided
    assert service.__class__.__name__.endswith("Service")
