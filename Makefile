# Biologic monorepo — оркестрация обеих подсистем.
# Backend (uv/make, Python 3.11) и frontend (bun) сохраняют свои инструменты;
# этот Makefile только запускает их из корня одной командой.

.PHONY: help install lint format test build typecheck e2e sdk-generate

help:
	@echo "Biologic monorepo"
	@echo "  make install       backend: uv sync  +  frontend: bun install"
	@echo "  make lint          backend: ruff+mypy  +  frontend: eslint+vue-tsc"
	@echo "  make format        backend: ruff format  +  frontend: eslint --fix"
	@echo "  make test          backend: pytest  +  frontend: bun test tests/shared"
	@echo "  make typecheck     frontend: vue-tsc"
	@echo "  make build         frontend: production build"
	@echo "  make e2e           frontend: playwright"
	@echo "  make sdk-generate  regenerate FE SDK from a running backend (:8080)"

install:
	cd backend && uv sync --all-extras
	cd frontend && bun install

lint:
	$(MAKE) -C backend lint
	cd frontend && bun run lint && bun run typecheck

format:
	$(MAKE) -C backend format
	cd frontend && bun run lint --fix || true

test:
	$(MAKE) -C backend test
	cd frontend && bun test tests/shared

typecheck:
	cd frontend && bun run typecheck

build:
	cd frontend && bun run build

e2e:
	cd frontend && bun run test:e2e

sdk-generate:
	cd frontend && bun run sdk:generate
