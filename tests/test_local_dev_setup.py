from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_env_example_documents_required_local_database_settings() -> None:
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert "APP_DATABASE_URL=" in env_example
    assert "APP_JWT_SECRET_KEY=" in env_example
    assert "APP_AUTH_COOKIE_SECURE=" in env_example
    assert "APP_AUTH_COOKIE_DOMAIN=" in env_example


def test_docker_compose_provisions_postgresql_15() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "postgres:15" in compose
    assert "POSTGRES_DB: biologic" in compose
    assert "POSTGRES_USER: biologic" in compose
    assert "5433:5432" in compose


def test_seed_test_data_script_has_main_entrypoint() -> None:
    script = (ROOT / "scripts" / "seed_test_data.py").read_text(encoding="utf-8")

    assert "async def seed_test_data" in script
    assert "asyncio.run" in script
