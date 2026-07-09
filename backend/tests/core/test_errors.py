from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from src.core.errors import DomainConflictError, ValidationError
from src.core.handlers import app_error_handler, validation_error_handler


def test_domain_conflict_error_uses_problem_details_shape() -> None:
    app = FastAPI()
    app.add_exception_handler(DomainConflictError, app_error_handler)

    @app.get("/boom")
    async def boom() -> None:
        raise DomainConflictError(
            code="invalid_status_transition",
            detail="Sample can be closed only from analyzed status.",
        )

    response = TestClient(app).get("/boom")

    assert response.status_code == 409
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json() == {
        "type": "https://api.example.com/errors/invalid-status-transition",
        "title": "Conflict",
        "status": 409,
        "detail": "Sample can be closed only from analyzed status.",
        "instance": "/boom",
        "errors": [],
        "code": "invalid_status_transition",
    }


def test_validation_error_uses_api_problem_details_uri() -> None:
    app = FastAPI()
    app.add_exception_handler(ValidationError, app_error_handler)

    @app.get("/invalid")
    async def invalid() -> None:
        raise ValidationError("Invalid payload.")

    response = TestClient(app).get("/invalid")

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json() == {
        "type": "https://api.example.com/errors/validation",
        "title": "Validation failed",
        "status": 422,
        "detail": "Invalid payload.",
        "instance": "/invalid",
        "errors": [],
    }


def test_request_validation_error_uses_api_problem_details_uri() -> None:
    app = FastAPI()
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    @app.get("/items")
    async def items(limit: int) -> dict[str, int]:
        return {"limit": limit}

    response = TestClient(app).get("/items?limit=not-an-int")

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    payload = response.json()
    assert payload["type"] == "https://api.example.com/errors/validation"
    assert payload["title"] == "Validation failed"
    assert payload["status"] == 422
    assert payload["detail"] == "One or more request fields are invalid."
    assert payload["instance"] == "/items"
    assert payload["errors"]
