from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from src.api.v1.router import router as api_v1_router
from src.core.config import Settings, get_settings
from src.core.errors import AppError
from src.core.handlers import app_error_handler, http_error_handler, validation_error_handler
from src.plugins.scalar import register as register_scalar


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=settings.openapi_url,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://192.168.3.1:5175",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://localhost:5175",
            "http://127.0.0.1:5175",
            "http://localhost:5176",
            "http://127.0.0.1:5176",
            "http://localhost:5177",
            "http://127.0.0.1:5177",
            "http://bio.tminww.space",
            "https://bio.tminww.space",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_scalar(app)
    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(HTTPException, http_error_handler)
    _register_spa(app, settings)
    return app


def _register_spa(app: FastAPI, settings: Settings) -> None:
    """Serve the built Vue SPA from `APP_STATIC_DIR` when it is configured.

    Registered last, so the API router, `/openapi.json` and the docs plugin
    keep priority. Hashed build assets are streamed by `StaticFiles`; every
    other path falls back to `index.html` for client-side routing. No-op in
    development, where `static_dir` is unset and Vite serves the frontend.
    """
    if not settings.static_dir:
        return

    static_dir = Path(settings.static_dir).resolve()
    index_file = static_dir / "index.html"
    if not index_file.is_file():
        return

    assets_dir = static_dir / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    # Reserved server-side prefixes that must never fall back to the SPA shell,
    # so an unknown API/doc path still yields a real 404 instead of index.html.
    reserved = tuple(
        p.strip("/")
        for p in (settings.api_v1_prefix, settings.openapi_url, "/docs")
        if p
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        # Segment-aware match: only exact reserved paths or their sub-paths are
        # excluded, so e.g. `docs-page` still resolves to the SPA, not a 404.
        if any(full_path == r or full_path.startswith(f"{r}/") for r in reserved):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = (static_dir / full_path).resolve()
        # Serve the requested file only if it stays inside static_dir
        # (guards against `..` traversal); otherwise hand back the SPA shell.
        if (
            full_path
            and candidate.is_file()
            and static_dir in candidate.parents
        ):
            return FileResponse(candidate)
        return FileResponse(index_file)
