from collections.abc import Mapping
from typing import Any


class AppError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        title: str,
        detail: str,
        type_uri: str = "about:blank",
        extra: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.title = title
        self.detail = detail
        self.type_uri = type_uri
        self.extra = dict(extra or {})


class NotFoundError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=404,
            title="Not Found",
            detail=detail,
            type_uri="https://example.local/problems/not-found",
        )


class BadRequestError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=400,
            title="Bad Request",
            detail=detail,
            type_uri="https://example.local/problems/bad-request",
        )


class ValidationError(AppError):
    def __init__(self, detail: str, *, extra: Mapping[str, Any] | None = None) -> None:
        super().__init__(
            status_code=422,
            title="Validation failed",
            detail=detail,
            type_uri="https://example.local/problems/validation-error",
            extra=extra,
        )


class UnauthorizedError(AppError):
    def __init__(self, detail: str = "Unauthorized.") -> None:
        super().__init__(
            status_code=401,
            title="Unauthorized",
            detail=detail,
            type_uri="https://example.local/problems/unauthorized",
        )
