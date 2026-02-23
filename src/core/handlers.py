from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.core.errors import AppError


def problem_response(
    *,
    request: Request,
    status_code: int,
    title: str,
    detail: str,
    type_uri: str = "about:blank",
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    payload: dict[str, Any] = {
        "type": type_uri,
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": str(request.url.path),
    }
    if extra:
        payload.update(extra)
    return JSONResponse(
        status_code=status_code,
        content=payload,
        media_type="application/problem+json",
    )


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, AppError):
        return problem_response(
            request=request,
            status_code=500,
            title="Internal Server Error",
            detail="Unexpected application error.",
        )
    return problem_response(
        request=request,
        status_code=exc.status_code,
        title=exc.title,
        detail=exc.detail,
        type_uri=exc.type_uri,
        extra=exc.extra,
    )


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    errors: list[Any] = []
    if isinstance(exc, RequestValidationError):
        errors = list(exc.errors())

    return problem_response(
        request=request,
        status_code=422,
        title="Validation failed",
        detail="One or more request fields are invalid.",
        type_uri="https://example.local/problems/validation-error",
        extra={"errors": errors},
    )


async def http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, HTTPException):
        status_code = exc.status_code
        detail = str(exc.detail)
    else:
        status_code = 500
        detail = "Unexpected HTTP-layer error."

    return problem_response(
        request=request,
        status_code=status_code,
        title="HTTP Error",
        detail=detail,
    )
