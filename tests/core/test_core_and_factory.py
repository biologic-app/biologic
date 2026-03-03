from __future__ import annotations

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request

from src.app_factory import create_app
from src.core.config import get_settings
from src.core.errors import AppError, BadRequestError
from src.core.handlers import (
    app_error_handler,
    http_error_handler,
    problem_response,
    validation_error_handler,
)


def make_request(path: str = "/test") -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [],
        "query_string": b"",
    }
    return Request(scope)


def test_settings_cache_and_defaults() -> None:
    settings_a = get_settings()
    settings_b = get_settings()

    assert settings_a is settings_b
    assert settings_a.api_v1_prefix == "/api/v1"


def test_problem_response_payload() -> None:
    request = make_request("/probe")
    response = problem_response(
        request=request,
        status_code=418,
        title="Teapot",
        detail="No coffee",
        type_uri="about:teapot",
        extra={"x": 1},
    )

    assert response.status_code == 418
    assert response.media_type == "application/problem+json"


async def test_app_error_handler_for_known_error() -> None:
    request = make_request("/errors")
    response = await app_error_handler(request, BadRequestError("bad"))

    assert response.status_code == 400


async def test_app_error_handler_for_unknown_error() -> None:
    request = make_request("/errors")
    response = await app_error_handler(request, Exception("boom"))

    assert response.status_code == 500


async def test_validation_error_handler() -> None:
    request = make_request("/validation")
    exc = RequestValidationError(
        [
            {
                "loc": ("query", "limit"),
                "msg": "invalid",
                "type": "value_error",
            }
        ]
    )
    response = await validation_error_handler(request, exc)

    assert response.status_code == 422


async def test_http_error_handler() -> None:
    request = make_request("/http")
    response = await http_error_handler(
        request, HTTPException(status_code=401, detail="unauthorized")
    )
    fallback = await http_error_handler(request, RuntimeError("oops"))

    assert response.status_code == 401
    assert fallback.status_code == 500


def test_create_app_and_health_endpoint() -> None:
    app = create_app()
    routes = {route.path for route in app.routes}

    assert "/api/v1/health" in routes
    assert "/docs" in routes


def test_app_error_attributes() -> None:
    exc = AppError(status_code=409, title="Conflict", detail="already exists", extra={"id": 1})

    assert str(exc) == "already exists"
    assert exc.status_code == 409
    assert exc.extra["id"] == 1
