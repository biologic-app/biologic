# Biologic — монорепозиторий (backend + frontend + docs)

Это **единый git-репозиторий** LIMS. Он объединяет backend, frontend и документацию,
чтобы агент видел весь контекст, а вертикальный слайс фичи делался одним PR.

```
biologic/            ← единый репозиторий (git)
├── backend/         ← FastAPI, uv, Python 3.11, PostgreSQL 15, :8080
├── frontend/        ← Vue 3, Vite, TypeScript, Nuxt UI, bun, :5177
├── docs/            ← единая документация (процессы, роли, фичи)
├── ROADMAP.md       ← план развития
├── Makefile         ← оркестрация обеих подсистем
└── .github/         ← CI (path-filtered)
```

> Это **единственный** файл правил агента в репозитории: отдельных `AGENTS.md` и
> `backend/CLAUDE.md` нет — всё здесь. Соглашения frontend и команды/архитектура backend —
> в разделах ниже.

## Контракт: OpenAPI

Граница между frontend и backend — OpenAPI-схема. Прямой импорт кода между подсистемами
запрещён; единственный канал — HTTP API.

```
backend (FastAPI) → /openapi.json → bun run sdk:generate → frontend/src/shared/api/generated
```

- Данные на проводе — **snake_case** (`VITE_API_REQUEST_CASE=snake`), на FE — `camelcase-keys`.
- API-префикс `/api/v1` (`VITE_API_PREFIX`).
- **Золотое правило:** любое изменение API в backend ⇒ обязательная регенерация SDK во
  frontend (`bun run sdk:generate`) + `bun run typecheck`. Несинхронизированный SDK —
  частый источник «зелёного» backend и красного frontend. Это часть DoD, не опция.

## Границы коммитов (обновлено: монорепо)

- Это **один** репозиторий — в отличие от прежней схемы двух отдельных репо.
  Вертикальный слайс (backend + SDK + frontend) может и **должен** идти одним PR.
- Стиль — **Conventional Commits** (англ., ≤72 символа): `feat:`, `fix:`, `refactor:`,
  `chore:`, `docs:`, `test:`. Scope приветствуется: `feat(auth):`, `fix(cart):`.
- Ветка по умолчанию — `master`. Коммит/пуш — **только по явной просьбе пользователя**.

## Порядок для фичи «сквозь стек»

1. **Backend** — реализовать и протестировать API (`make be-test be-lint`).
2. **SDK** — регенерировать клиент (`cd frontend && bun run sdk:generate`).
3. **Frontend** — реализовать UI поверх нового клиента (`bun run typecheck lint build`).
4. Один PR на весь слайс; e2e (k6 + Playwright) и запись видео — по конвейеру (ROADMAP §A3).

## Верификация (определение «готово»)

- Из корня: `make lint` (ruff+mypy + eslint+vue-tsc), `make test`, `make build`.
- Backend: `make be-lint be-test` (детали — раздел «Backend» ниже).
- Frontend: `cd frontend && bun run lint typecheck build` + `bun test tests/shared`.
- Контракт: после изменения API сгенерированный SDK компилируется без ошибок.

## Frontend — соглашения

Структура: bootstrap в `src/main.ts` и `src/app/`; страницы в `src/pages/`; фичи в
`src/modules/` (`auth`, `directions`, `research`, `dictionaries`, `access`, …); общий код в
`src/shared/` (`ui`, `composables`, `api`, `types`, `utils`, `i18n`, `config`). Держи
код фичи внутри её модуля; переиспользуемое — в `src/shared/`.

- **Только явные импорты — auto-imports запрещены.** Каждый символ импортируется явно:
  Vue API (`ref`, `computed`, `watch`), composables (`useToast`, `useRoute`, `useAuth`),
  компоненты Nuxt UI (`UButton`, `UTable`, …). Плагины авто-импорта и генерируемые
  `auto-imports.d.ts`/`components.d.ts` подлежат удалению (ROADMAP D6); новый код уже
  пишется с явными импортами.
- Импорты из `src` — через алиас `@/` (например `@/shared/utils/format`).
- Компоненты — PascalCase (`UserMenu.vue`); composables — `useX` (`useAuth.ts`).
- TypeScript со строгими проверками. ESLint: `typescript-eslint` + `eslint-plugin-vue`
  (flat recommended); в шаблонах ≤3 атрибутов в строку.
- Проверка (тест-раннера как такового мало): `bun run lint typecheck build` +
  `bun test tests/shared` + e2e `bun run test:e2e` (Playwright).
- `.editorconfig`: 2 пробела, LF, UTF-8, финальный перевод строки.

## Backend — команды и архитектура

FastAPI, SQLAlchemy 2.0 async, PostgreSQL 15, DDD. Команды — через корневой Makefile
(`make be-*`) или напрямую в `backend/`.

### Команды
- `make be-dev` — uvicorn --reload :8080
- `make be-test` — pytest
- `make be-lint` — ruff check + mypy
- `make be-format` — ruff format
- `make be-audit` — pip-audit
- `make be-seed-data` — справочные данные
- `make be-k6-scenarios` — k6-сценарии (нужен запущенный API)

Один тест: `cd backend && uv run pytest -v tests/path/to/test_file.py::test_name`.
Миграции: `cd backend && uv run alembic upgrade head` /
`uv run alembic revision --autogenerate -m "description"`.
Docker dev: `cd backend && docker compose up --build` — API :8080, PostgreSQL 15.

### DDD Bounded Contexts

> Текущий снимок; DDD-консолидация до одного контекста — в процессе (ROADMAP D1).

Контексты под `src/contexts/` (часть уже вынесена в плоские `src/{domain,application,
infrastructure,presentation}`): `laboratory_workflow` (направления, образцы, исследования,
тесты, протоколы — ядро), `catalogs` (справочники CRUD), `access_control` (RBAC),
`audit` (`change_log`), `notifications` (alerts), `dashboard` (read-проекции).

### Слои (DIP-стек)
- `domain/` — чистый Python, без framework-импортов (статус-политики, доменные события,
  value objects). Не импортирует FastAPI/SQLAlchemy (тест `test_domain_does_not_import_...`).
- `application/` — порты (Protocol), DTO, command-сервисы. Зависит только от domain.
- `infrastructure/` — SQLAlchemy-репозитории, реализующие порты application.
- `presentation/` — FastAPI-роутеры, Pydantic-схемы, DI. `core/` не импортирует из contexts.

### API Design
Префикс `/api/v1`. Два паттерна: **CRUD** (`GET/POST/PATCH/DELETE /{resource}`, пагинация
`offset/limit/sort_by/sort_order/filters/include`; список `{items, meta}`, чтение `{data, meta}`)
и **Команды** (`POST /{resource}/{id}/{action}` → `{data: CommandResult, meta: {operation}}`).
Смена статуса жизненного цикла — только через команды, никогда `PATCH status_id`. Спецификация:
`docs/architecture/2026-05-14-backend-mvp-ddd-api-design.md`.

### Status Codes
Лайфсайкл-сущности ссылаются на статус-таблицы по UUID; стабильные `code`-строки — авторитет
для UI и переходов (`src/core/status_codes.py`):
```
DIRECTION: draft → registered → in_progress → partially_completed → completed
SAMPLE:    pending → registered → in_progress → analyzed → completed;  → rejected;  analyzed → in_progress (reopen)
RESEARCH:  draft → ordered → in_progress → completed;  draft/ordered → rejected
TEST:      queued → in_progress → completed;  → rejected;  in_progress → queued (requeue)
```
Правила переходов — `src/contexts/laboratory_workflow/domain/status_policy.py`.

### Errors
Problem-details (`application/problem+json`, `src/core/errors.py`): `AppError` (база),
`NotFoundError(404)`, `BadRequestError(400)`, `ValidationError(422)`, `DomainConflictError(409)`,
`UnauthorizedError(401)`, `ForbiddenError(403)`. Правило scope: сущность вне scope → 404;
в scope без права → 403.

### Database / Auth
SQLAlchemy 2.0 async + asyncpg; модели в `src/infrastructure/db/models/`, все от `Base`;
UUIDv7 PK (`uuidv7()` server default), поля `created_at/updated_at/deleted_at`. Сессия —
`get_db_session` в `src/core/database.py`. Auth: JWT access/refresh в cookie; настройки —
`APP_`-префикс (`src/core/config.py`); bcrypt via `passlib`; RBAC-политика —
`src/contexts/access_control/domain/policy.py`.

### Ключевые файлы
`src/main.py` (entry), `src/app_factory.py` (сборка app), `src/api/v1/router.py`,
`src/core/{config,database,errors,handlers,responses,pagination,status_codes}.py`,
`src/infrastructure/db/models/`.

## Инструментарий (не смешивать)

- Backend — только `uv`/`make`, Python 3.11.
- Frontend — только `bun` (закреплено `packageManager` и `bun.lock`).

## Секреты

Реальные `.env` не коммитятся. Шаблоны: `backend/.env.example` (`APP_`-префикс),
`frontend/.env.example` (`VITE_`-префикс).

<!-- smithers:prefer-workflows START -->
## Smithers workflows

Use your best judgment, weighing speed, quality, and token usage, to decide
whether a request should run as a [smithers.sh](https://smithers.sh) workflow
or with regular subagents. Prefer a smithers workflow for multi-step plans and
for work that benefits from retries, approvals, review, or replay; reach for
plain subagents when a request is a quick one-off.

The `smithers` skill is installed: run `smithers workflow list` to see the
available workflows and `smithers workflow run <id>` to launch one.

When a session ends successfully and the work could have been a smithers
workflow, offer to turn the session into a reusable smithers workflow for next
time.
<!-- smithers:prefer-workflows END -->
