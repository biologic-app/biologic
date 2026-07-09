SEED_ARGS ?=
ANALYZE_QUERY_ARGS ?= --seed-profile perf-lite --truncate --database-url postgresql://biologic:biologic@localhost:5433/biologic
UV_RUN ?= uv run
K6 ?= k6
K6_BASE_URL ?= http://localhost:8080/api/v1

# k6 contexts bundled into the combined run. Override on the CLI, e.g.
#   make k6-scenarios K6_CONTEXTS="workflow"
K6_CONTEXTS ?= workflow
K6_ALL_JSON := $(foreach c,$(K6_CONTEXTS),reports/k6/$(c)-results.json)

.PHONY: dev test lint format audit seed-data analyze-orm-queries k6-workflow k6-functional k6-scenarios

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

# --- k6 (functional scenarios) ----------------------------------------------
# Needs the API running (make dev) on a migrated database. Reports land in
# reports/k6/ and the run fails on a breached threshold (checks rate==1.00).

k6-workflow: ## k6 context: laboratory_workflow command guardrail suite
	@mkdir -p reports/k6
	BASE_URL=$(K6_BASE_URL) $(K6) run --out json=reports/k6/workflow-results.json \
		tests/k6/scenarios/workflow/index.js
	$(UV_RUN) python -m scripts.k6_report_visual reports/k6/workflow-results.json \
		--title "Biologic — Workflow" --base-url $(K6_BASE_URL)

k6-functional: k6-workflow ## k6: all context scenarios (full run)

k6-scenarios: ## k6: run every K6_CONTEXTS context as one bundle → single combined report
	@mkdir -p reports/k6
	@rc=0; for ctx in $(K6_CONTEXTS); do \
		echo "── k6 scenarios: $$ctx ──"; \
		BASE_URL=$(K6_BASE_URL) $(K6) run \
			--out json=reports/k6/$$ctx-results.json \
			tests/k6/scenarios/$$ctx/index.js || rc=1; \
	done; \
	echo "── building combined report ──"; \
	$(UV_RUN) python -m scripts.k6_report_visual $(K6_ALL_JSON) \
		-o reports/k6/all-results.html \
		--title "Biologic — All Scenarios" --base-url $(K6_BASE_URL); \
	exit $$rc
