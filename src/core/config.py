from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

CORE_DIR = Path(__file__).resolve().parent
APP_DIR = CORE_DIR.parent


class Settings(BaseSettings):
    app_name: str = "Biologic System Backend API"
    api_v1_prefix: str = "/api/v1"
    debug: bool = False
    docs_url: str | None = "/docs"
    openapi_url: str = "/openapi.json"
    is_dev: bool = True
    database_url: str = "postgresql+asyncpg://biologic:biologic@127.0.0.1:5432/biologic"
    alembic_database_url: str = "postgresql+asyncpg://biologic:biologic@127.0.0.1:5432/biologic"
    plugins_dir: Path = APP_DIR / "plugins"
    jwt_secret_key: str = "change-me-local-jwt-secret"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    access_cookie_name: str = "access_token"
    refresh_cookie_name: str = "refresh_token"
    auth_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    auth_cookie_secure: bool | None = None
    auth_cookie_domain: str | None = None
    auth_cookie_path: str = "/"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
