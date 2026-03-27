from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1.router import router as api_v1_router
from src.core.config import get_settings
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
    return app
