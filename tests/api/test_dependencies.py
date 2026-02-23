from __future__ import annotations

import inspect

import pytest

from src.api import dependencies

SERVICE_PROVIDERS = [
    func
    for _, func in inspect.getmembers(dependencies, inspect.isfunction)
    if func.__name__.startswith("get_") and func.__name__.endswith("_service")
]


@pytest.mark.parametrize("provider", SERVICE_PROVIDERS)
def test_dependency_provider_returns_service(provider) -> None:
    service = provider(db_session=object())
    assert service.__class__.__name__.endswith("Service")
