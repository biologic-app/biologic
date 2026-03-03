UV ?= uv
UV_CACHE_DIR ?= /tmp/uv-cache
SEED_ARGS ?= --profile dev --database-url postgresql://biologic:biologic@127.0.0.1:5432/biologic
ANALYZE_QUERY_ARGS ?= --seed-profile perf-lite --truncate --database-url postgresql://biologic:biologic@localhost:5432/biologic

.PHONY: biologic-api seed-data analyze-orm-queries

biologic-api:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) run uvicorn src.main:app --reload --port 8080

seed-data:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) run python -m scripts.seed_data $(SEED_ARGS)

analyze-orm-queries:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) run python -m scripts.analyze_orm_query_plans $(ANALYZE_QUERY_ARGS)
