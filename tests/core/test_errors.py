from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.errors import DomainConflictError
from src.core.handlers import app_error_handler


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
