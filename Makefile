SEED_ARGS ?=
ANALYZE_QUERY_ARGS ?= --seed-profile perf-lite --truncate --database-url postgresql://biologic:biologic@localhost:5433/biologic

.PHONY: dev test lint format audit seed-data analyze-orm-queries

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
	uv run python -m scripts.seed_test_data $(SEED_ARGS)

analyze-orm-queries:
	uv run python -m scripts.analyze_orm_query_plans $(ANALYZE_QUERY_ARGS)
