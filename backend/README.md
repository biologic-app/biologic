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

## Local PostgreSQL (dev)

Start PostgreSQL 15:

```bash
docker compose up -d postgres
```

Apply migrations and seed a small test dataset:

```bash
uv run alembic upgrade head
make seed-data
```

Generate larger workflow datasets for frontend and pagination testing:

```bash
make seed-data SEED_ARGS="--count 1000"
make seed-data SEED_ARGS="--count 1000000 --truncate-generated"
```

`--count` creates that many generated `research` rows with related
`directions`, `samples`, and `tests`. `--truncate-generated` deletes only
previously generated bulk workflow rows before creating the new set.

## Legacy MySQL 5.1 ETL

The standalone importer reads the immutable PostgreSQL staging copy of the
legacy dump. It is read-only by default and prints source counts/orphans:

```bash
make be-import-legacy
```

To write canonical rows, pass `--apply` explicitly (and override the target
DSN when testing in an isolated database):

```bash
make be-import-legacy LEGACY_ETL_ARGS="--apply --target-database-url postgresql://..."
```

Для безопасной проверки записи используйте ограниченный smoke-test:

```bash
make be-import-legacy LEGACY_ETL_ARGS="--apply --limit 100 --target-database-url postgresql://..."
```

Mapping is externalized in `config/legacy_etl_mapping.json`. Validate a changed
file without connecting to either database:

```bash
uv run python -m scripts.import_legacy_mysql \
  --mapping-file config/legacy_etl_mapping.json \
  --validate-mapping
```

The JSON controls enabled entities, source/target table names, source/target
columns, value dictionaries, extra attributes, and flat additional tables.

The importer never deletes source or canonical rows. It uses deterministic
UUID mappings in `legacy_import.id_map` and records unresolved foreign keys and
password-reset requirements in `legacy_import.warning`. See
`docs/architecture/legacy-mysql-postgres-mapping.md` for the full conversion
contract.

Local defaults are documented in `.env.example`; `.env` points the app at
PostgreSQL 15 on `127.0.0.1:5433`.
