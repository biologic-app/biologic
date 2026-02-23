from __future__ import annotations

import importlib

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from src.core import database


def test_engine_and_session_factory_singletons() -> None:
    database.get_engine.cache_clear()
    database.get_session_factory.cache_clear()

    engine_a = database.get_engine()
    engine_b = database.get_engine()
    factory_a = database.get_session_factory()
    factory_b = database.get_session_factory()

    assert isinstance(engine_a, AsyncEngine)
    assert engine_a is engine_b
    assert factory_a is factory_b


def test_get_db_session_yields_async_session() -> None:
    async def _run() -> None:
        generator = database.get_db_session()
        session = await anext(generator)
        assert isinstance(session, AsyncSession)
        await generator.aclose()

    import asyncio

    asyncio.run(_run())


def test_main_module_exposes_app() -> None:
    module = importlib.import_module("src.main")
    assert module.app is not None
