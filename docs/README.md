# Документация Biologic

Единая точка входа в документацию монорепо. Пока исторические документы живут внутри
подсистем (перенесены сюда в рамках этапа A2 роадмапа — консолидация документации).

## План развития
- [ROADMAP.md](../ROADMAP.md) — этапы развития проекта.

## Backend
- `backend/docs/architecture/backend-architecture-review.md` — целевая DDD-архитектура.
- `backend/docs/architecture/backend-ddd-contexts.md` — bounded contexts.
- `backend/docs/architecture/schema-vs-backend-diff.md` — расхождения модели данных и ORM.
- `backend/docs/adr/` — архитектурные решения (ADR).

## Frontend
- `frontend/docs/frontend-user-stories.md` — 13 фич с acceptance criteria.
- `frontend/docs/role-access-matrix.md` — матрица `роль × ресурс × действие × scope`.
- `frontend/docs/login-backend-integration-plan.md` — план реальной авторизации.
- `frontend/docs/frontend-refactor-plan.md` — рефакторинг FE (7 фаз).
- `frontend/docs/work-processes-by-roles.md`, `frontend/docs/statuses.md`, `frontend/docs/flows/`.

## Планируется (этап A2)
- `docs/processes/user-actions.md` — сквозная диаграмма действий всех ролей + карта автоматизации.
- `docs/roles/` — процессные описания по каждой роли.
- `docs/processes/feature-pipeline.md` — конвейер создания фич (issue → слайс → видео).
- `docs/processes/legacy-protocol.md` — разбор формирования xlsx-протокола старой программой.
