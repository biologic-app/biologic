from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

APP_DIR = Path(__file__).resolve().parents[1]
BASE_DIR = APP_DIR.parent


class Settings(BaseSettings):
    app_name: str = "Biologic System Backend API"
    api_v1_prefix: str = "/api/v1"
    debug: bool = False
    docs_url: str | None = "/docs"
    openapi_url: str = "/openapi.json"
    is_dev: bool = True
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_ttl_seconds: int = 40
    refresh_token_ttl_seconds: int = 60
    access_cookie_name: str = "access_cookie"
    refresh_cookie_name: str = "refresh_cookie"
    auth_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    auth_cookie_secure: bool
    auth_cookie_domain: str
    auth_cookie_path: str = "/"
    # Absolute path to the built frontend (Vite `dist`). When set and the
    # directory exists, the app serves the SPA + static assets itself, so a
    # single uvicorn process covers both `/api/v1` and the UI (offline Windows
    # deploy). Left unset in development, where Vite serves the frontend.
    static_dir: str | None = None

    @property
    def plugins_dir(self) -> Path:
        return APP_DIR / "plugins"

    model_config = SettingsConfigDict(
        env_file=f"{BASE_DIR}/.env",
        env_prefix="APP_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
