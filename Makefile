
SEED_ARGS ?= --profile dev --database-url postgresql://biologic:biologic@127.0.0.1:5432/biologic
ANALYZE_QUERY_ARGS ?= --seed-profile perf-lite --truncate --database-url postgresql://biologic:biologic@localhost:5432/biologic

.PHONY: run test lint format audit seed-data analyze-orm-queries

dev:
	uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8080

test:
	uv run pytest -v

lint:
	uv run ruff check src tests
	uv run mypy src tests

format:
	uv run ruff format src tests

audit:
	uv run pip-audit

seed-data:
	uv run python -m scripts.seed_data $(SEED_ARGS)

analyze-orm-queries:
	uv run python -m scripts.analyze_orm_query_plans $(ANALYZE_QUERY_ARGS)