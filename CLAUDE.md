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

> Это **единственный** файл правил агента в репозитории (отдельных `AGENTS.md` в
> подсистемах нет). Детали backend — в `backend/CLAUDE.md`; соглашения frontend — в
> разделе ниже.

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

1. **Backend** — реализовать и протестировать API (`make -C backend test lint`).
2. **SDK** — регенерировать клиент (`cd frontend && bun run sdk:generate`).
3. **Frontend** — реализовать UI поверх нового клиента (`bun run typecheck lint build`).
4. Один PR на весь слайс; e2e (k6 + Playwright) и запись видео — по конвейеру (ROADMAP §A3).

## Верификация (определение «готово»)

- Из корня: `make lint` (ruff+mypy + eslint+vue-tsc), `make test`, `make build`.
- Backend: `make -C backend lint test` (детали — `backend/CLAUDE.md`).
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

## Инструментарий (не смешивать)

- Backend — только `uv`/`make`, Python 3.11.
- Frontend — только `bun` (закреплено `packageManager` и `bun.lock`).

## Секреты

Реальные `.env` не коммитятся. Шаблоны: `backend/.env.example` (`APP_`-префикс),
`frontend/.env.example` (`VITE_`-префикс).
