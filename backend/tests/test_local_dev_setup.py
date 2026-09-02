from pathlib import Path
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncConnection

from scripts import seed_test_data

ROOT = Path(__file__).resolve().parents[1]


def test_env_example_documents_required_local_database_settings() -> None:
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert "APP_DATABASE_URL=" in env_example
    assert "APP_JWT_SECRET_KEY=" in env_example
    assert "APP_AUTH_COOKIE_SECURE=" in env_example
    assert "APP_AUTH_COOKIE_DOMAIN=" in env_example


def test_docker_compose_provisions_postgresql_15() -> None:
    compose = (ROOT / "docker-compose.yaml").read_text(encoding="utf-8")

    assert "postgres:15" in compose
    assert "POSTGRES_DB: biologic" in compose
    assert "POSTGRES_USER: biologic" in compose
    assert "5433:5432" in compose


def test_seed_test_data_script_has_main_entrypoint() -> None:
    script = (ROOT / "scripts" / "seed_test_data.py").read_text(encoding="utf-8")

    assert "async def seed_test_data" in script
    assert "asyncio.run" in script


def test_seed_test_data_cli_accepts_bulk_generation_options() -> None:
    args = seed_test_data._parse_args(
        [
            "--count",
            "1_000",
            "--batch-size",
            "250",
            "--truncate-generated",
        ]
    )

    assert args.count == 1000
    assert args.batch_size == 250
    assert args.truncate_generated is True


def test_seed_test_data_batches_large_counts() -> None:
    batches = list(seed_test_data._iter_seed_batches(total_count=25_001, batch_size=10_000))

    assert batches == [(1, 10_000), (10_001, 20_000), (20_001, 25_001)]


async def test_seed_test_data_bulk_generation_uses_generate_series_batches() -> None:
    class FakeConnection:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, Any]]] = []

        async def execute(self, statement: object, params: dict[str, Any]) -> None:
            self.calls.append((str(statement), params))

    connection = FakeConnection()

    await seed_test_data._seed_generated_workflow_rows(
        cast(AsyncConnection, connection),
        count=25_001,
        batch_size=10_000,
    )

    assert len(connection.calls) == 3
    assert connection.calls[0][1]["indices"] == list(range(1, 10_001))
    assert connection.calls[2][1]["indices"] == list(range(20_001, 25_002))
    for _, params in connection.calls:
        row_count = len(params["indices"])
        for key in ("direction_ids", "sample_ids", "research_ids", "test_ids"):
            assert len(params[key]) == row_count
            assert len({str(v) for v in params[key]}) == row_count  # all distinct
    normalized_sql = [" ".join(sql.split()) for sql, _ in connection.calls]
    assert all("unnest(" in sql for sql in normalized_sql)
    assert all("CAST(:indices AS integer[])" in sql for sql in normalized_sql)
    assert all("CAST(:direction_ids AS uuid[])" in sql for sql in normalized_sql)
