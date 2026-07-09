# Документация Biologic

Единая документация монорепо. Разбита по назначению: архитектура, продукт (что система
делает), роли, процессы (как ведётся разработка), frontend-специфика.

```
docs/
├── architecture/   архитектура backend, ADR, спецификация API
├── product/        что система делает: user stories, роли×права, статусы, планы
├── roles/          процессные описания по каждой роли (регистратор, врач, …)
├── processes/      как ведётся разработка: диаграмма действий, конвейер фич, легаси
└── frontend/       FE-специфика: план рефакторинга, ревью, flow-сценарии + видео
```

## Архитектура — `architecture/`
- [backend-architecture-review.md](architecture/backend-architecture-review.md) — целевая DDD-архитектура (модульный монолит, EventBus).
- [backend-ddd-contexts.md](architecture/backend-ddd-contexts.md) — bounded contexts.
- [schema-vs-backend-diff.md](architecture/schema-vs-backend-diff.md) — расхождения справочной модели данных и ORM.
- [2026-05-14-backend-mvp-ddd-api-design.md](architecture/2026-05-14-backend-mvp-ddd-api-design.md) — спецификация API (CRUD + команды).
- [adr/](architecture/adr/) — архитектурные решения (ADR).

## Продукт — `product/`
- [frontend-user-stories.md](product/frontend-user-stories.md) — 13 фич с acceptance criteria (источник DoD).
- [role-access-matrix.md](product/role-access-matrix.md) — матрица `роль × ресурс × действие × scope` + демо-учётки.
- [statuses.md](product/statuses.md) — жизненные циклы статусов (направление/образец/исследование/тест).
- [work-processes-by-roles.md](product/work-processes-by-roles.md) — рабочие процессы по ролям.
- [login-backend-integration-plan.md](product/login-backend-integration-plan.md) — пошаговый план реальной авторизации.

## Роли — `roles/`
- [roles/README.md](roles/README.md) — индекс и шаблон ролевых документов (этап A2.2 роадмапа).

## Процессы — `processes/`
- [user-actions.md](processes/user-actions.md) — сквозная диаграмма действий всех ролей + карта автоматизации (A2.1).
- [feature-pipeline.md](processes/feature-pipeline.md) — конвейер создания фич: issue → слайс → видео (A3).
- [legacy-protocol.md](processes/legacy-protocol.md) — разбор формирования xlsx-протокола старой программой (C4.1).

## Frontend — `frontend/`
- [frontend-refactor-plan.md](frontend/frontend-refactor-plan.md) — рефакторинг FE (7 фаз, −3500 LOC).
- [frontend-code-review.md](frontend/frontend-code-review.md) · [frontend-tables-code-review.md](frontend/frontend-tables-code-review.md) — ревью.
- [flows/](frontend/flows/) — flow-сценарии (registrator, sanitary-doctor, lab-doctor) + записи видео.

---

Общий план развития — [../ROADMAP.md](../ROADMAP.md).
