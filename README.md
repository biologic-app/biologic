# Biologic — LIMS (монорепозиторий)

Единый репозиторий лабораторной информационной системы: **backend** (FastAPI, DDD),
**frontend** (Vue 3, Nuxt UI) и **документация** в одном месте — чтобы вертикальный
слайс фичи (от UI до API) делался в одном PR.

```
biologic/
├── backend/    FastAPI · uv · Python 3.11 · PostgreSQL 15 · :8080   (см. backend/CLAUDE.md)
├── frontend/   Vue 3 · Vite · TypeScript · Nuxt UI · bun · :5177    (соглашения — в CLAUDE.md)
├── docs/       единая документация (процессы, роли, фичи)
├── ROADMAP.md  план развития проекта
└── .github/    CI (path-filtered: backend / frontend)
```

## Контракт между backend и frontend — OpenAPI

Единственный канал интеграции — HTTP API. Backend публикует `/openapi.json`; frontend
генерирует типизированный TS-клиент (`bun run sdk:generate` → `src/shared/api/generated`).
**Любое изменение API ⇒ регенерация SDK** — часть определения «готово».

## Быстрый старт

```bash
make install        # backend: uv sync  +  frontend: bun install
make lint           # ruff+mypy (backend)  +  eslint+vue-tsc (frontend)
make test           # pytest (backend)  +  bun test (frontend)

# запуск (два терминала):
cd backend  && docker compose up -d && uv run alembic upgrade head && make dev   # :8080
cd frontend && bun run sdk:generate && bun run dev                               # :5177
```

## Разработка

- Backend — только `uv`/`make` (не pip/poetry), Python 3.11.
- Frontend — только `bun` (не npm/yarn/pnpm).
- Коммиты — Conventional Commits (англ., ≤72 символа); вертикальный слайс = один PR.
- Ветка по умолчанию — `master`.

Подробный план — в [ROADMAP.md](./ROADMAP.md).
