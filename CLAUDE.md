# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
make dev           # uvicorn --reload :8080
make test          # uv run pytest -v
make lint          # ruff check + mypy src tests
make format        # ruff format src tests
make audit         # uv run pip-audit
make seed-data     # seed reference data
```

Run single test:

```bash
uv run pytest -v tests/path/to/test_file.py::test_name
```

Alembic migrations (configure `sqlalchemy.url` in alembic.ini first):

```bash
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "description"
```

Docker dev: `docker compose up --build` — API on `:8080`, PostgreSQL 15 on `:5432`.

## Architecture

### DDD Bounded Contexts

Five bounded contexts under `src/contexts/`:

| Context | Role |
|---------|------|
| `laboratory_workflow` | Directions, samples, research, tests, protocols — the core workflow lifecycle |
| `catalogs` | Reference data CRUD: branches, labs, objects, doctors, sample_types, research_goals, indicators, conclusions, protocol_types |
| `access_control` | Users, roles, permissions, scopes, RBAC policy |
| `audit` | Immutable `change_log` (history) for all CRUD and domain events |
| `notifications` | System-created `alerts`, user mark-read/hide commands |

### Context Layers (DIP Stack)

Each context follows a strict dependency-inversion stack:

- `domain/` — pure Python, no framework imports. Status policies, domain events, value objects. Never imports FastAPI or SQLAlchemy (enforced by `test_domain_does_not_import_fastapi_or_sqlalchemy`).
- `application/` — ports (Protocol interfaces), DTOs, command services. Depends on domain only.
- `infrastructure/` — SQLAlchemy repositories implementing application ports. Depends on `src.infrastructure.db.models`.
- `presentation/` — FastAPI routers, Pydantic request schemas, DI wiring. Depends on application ports + infrastructure.

Rule: `core/` modules must never import from `contexts/` (enforced by `test_core_does_not_import_contexts`).

### API Design

Base prefix: `/api/v1`. Two endpoint patterns:

1. **CRUD** — `GET/POST/PATCH/DELETE /{resource}` with pagination params (`offset`, `limit`, `sort_by`, `sort_order`, `filters`, `include`). List response: `{items, meta}`. Read response: `{data, meta}`. See `src/core/responses.py`.

2. **Commands** — `POST /{resource}/{id}/{action}`. Returns `{data: CommandResult, meta: {operation}}`. Lifecycle status changes MUST go through commands, never `PATCH status_id`. See spec at `docs/superpowers/specs/2026-05-14-backend-mvp-ddd-api-design.md`.

### Status Codes

All lifecycle entities reference status tables by UUID. Stable `code` strings are the authority for UI logic and transitions:

```python
# src/core/status_codes.py
DIRECTION: draft → registered → in_progress → partially_completed → completed
SAMPLE:    pending → registered → in_progress → analyzed → completed
           pending/registered/in_progress → rejected
           analyzed → in_progress (reopen)
RESEARCH:  draft → ordered → in_progress → completed
           draft/ordered → rejected
           completed → in_progress (reopen on add-tests)
TEST:      queued → in_progress → completed
           queued/in_progress → rejected
           in_progress → queued (requeue)
```

Status transition rules: `src/contexts/laboratory_workflow/domain/status_policy.py`.

### Errors

Problem-details style (`application/problem+json`) via `src/core/errors.py`:

- `AppError` base — status, title, detail, type_uri, extra
- `NotFoundError (404)`, `BadRequestError (400)`, `ValidationError (422)`, `DomainConflictError (409)`, `UnauthorizedError (401)`, `ForbiddenError (403)`

Scope rule: entity exists but outside user scope → 404. Entity in scope but no permission → 403.

### Database

SQLAlchemy 2.0 async with asyncpg. Models in `src/infrastructure/db/models/entities.py` — all extend declarative `Base`. Use UUIDv7 primary keys via `uuidv7()` server default. All tables have `created_at/updated_at` and soft-delete `deleted_at`.

Session DI: `get_db_session` in `src/core/database.py` → FastAPI dep injection.

### Auth

JWT access/refresh token pair in cookies. Settings via `APP_` env prefix (see `src/core/config.py`). Password hashing: bcrypt via `passlib`. RBAC policy: `src/contexts/access_control/domain/policy.py` — role-key → permission set mapping.

### Key Source Files

| File | Purpose |
|------|---------|
| `src/main.py` | Entry point |
| `src/app_factory.py` | FastAPI app assembly (middleware, routers, error handlers) |
| `src/api/v1/router.py` | Top-level v1 router (health, sub-routers) |
| `src/core/config.py` | Pydantic settings from `.env` |
| `src/core/database.py` | Async engine, session factory |
| `src/core/errors.py` | AppError hierarchy |
| `src/core/handlers.py` | Problem+json error handlers |
| `src/core/responses.py` | `SingleResponse[T]`, `ListResponse[T]` |
| `src/core/pagination.py` | `PaginationParams`, `PageMeta` |
| `src/core/status_codes.py` | Status code string constants |
| `src/infrastructure/db/models/entities.py` | All SQLAlchemy ORM models |
