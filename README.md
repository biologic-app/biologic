# Biologic System Backend

Backend for a laboratory information system built with Python 3.11.2 and FastAPI.

## Current Focus

The current stage defines project conventions and architecture before implementation:

- Layered architecture and dependency rules
- CRUD API conventions with pagination and filtering
- Error contract (`RFC 9457`, `application/problem+json`)
- Testing and quality standards
- Documentation workflow with Zensical and i18n support

## Documentation

Project documentation source is `docs/`.

- Zensical config: `zensical.toml` (unchanged, fully compatible).
- Scalar config: `scalar.config.json` (now also reads from `docs/`).
- Legacy Scalar starter pages are preserved in `scalar-docs/` for comparison.

Run API locally:

```bash
make api-run
```

Open FastAPI Swagger UI:

- `http://127.0.0.1:8000/docs`

Run Scalar docs with your current Scalar command and `scalar.config.json`.

Run project docs locally (with embedded Swagger page):

```bash
make docs-serve
```

Build docs strictly:

```bash
make docs-build
```

## Docker (dev)

Run API + PostgreSQL 15 + Alembic migrations:

```bash
docker compose up --build
```

Services:

- API: `http://127.0.0.1:8080`
- Health: `http://127.0.0.1:8080/api/v1/health`
- PostgreSQL 15: `127.0.0.1:5432`
