---
created: 2026-07-19
tags:
  - biologic
  - registrar
  - lab_doctor
  - workflow
  - plan
---

# План: рестайл справочников/доступа + упрощение рабочего процесса регистратора и ВЛ

> Источник — запрос владельца (2026-07-19). Документ фиксирует, что **уже
> сделано** в этой сессии (Части A–B, только frontend, без миграций), и
> **детальный план** оставшихся изменений (Части C–F), которые затрагивают
> backend/миграции/SDK/e2e и требуют подтверждения продуктовых решений
> (см. «Открытые решения»). Ссылается на `docs/product/statuses.md`,
> `docs/frontend/flows/registrator.flow.md`, `docs/frontend/flows/lab-doctor.flow.md`,
> `ROADMAP.md` (C1.4, C2, C4).

## Цели (из запроса)

1. Справочники и таблицы доступа — привести к стилистике страницы
   «Направления». **(Сделано, Часть A.)**
2. «Подписки» перенести в группу «Доступ». **(Сделано, Часть B.)**
3. Упростить статусную модель **исследований** и **испытаний**. (Часть C.)
4. При регистрации направления **автоматически назначать цели исследования**
   образцам. (Часть D.)
5. Образец **выпускается из лаборатории**; регистратор делает **протокол на
   образцы или на целое направление**. (Часть E.)
6. У регистратора — **окно выпущенных образцов, сгруппированных по
   направлениям**, для формирования протоколов. (Часть F, = ROADMAP C1.4.)
7. Прогнать e2e Playwright **с записью видео** для регистратора и врача
   лаборатории. (Часть G — отдельный Sonnet-субагент.)

---

## Часть A — Рестайл справочников и доступа под стиль «Направлений» ✅ СДЕЛАНО

Эталон — `src/shared/ui/WorkflowCrudPage.vue` (панель + один тулбар:
поиск + фильтры + обновить + столбцы; «Создать» — в слоте `#navbar-right`).

Изменения:
- **`WorkflowCrudPage.vue`** — добавлен слот `#toolbar-extra` между навбаром и
  тулбаром поиска (для доп. nav-меню). Страницы рабочих процессов
  (Направления/Образцы) слот не используют — их вид не меняется.
- **`DictionariesPage.vue`** — переписана поверх `WorkflowCrudPage`:
  nav-меню категорий и под-меню статусов уехали в `#toolbar-extra`, кнопка
  «Создать» — в `#navbar-right`, массовое удаление — в оверлей выделения
  (как в Направлениях), **появилась кнопка «Фильтр»** (`CrudFilterControls`),
  которой раньше не было. `:key="moduleKey"` пересобирает таблицу при смене
  справочника.
- **`UsersPage.vue`, `UserTypesPage.vue` (таблицы доступа)** — тулбар выровнен
  под эталон: добавлен `CrudFilterControls` (открывает существующую
  `CrudFilterModal`), убрана дублирующая инлайновая кнопка «Удалить» (удаление
  доступно из оверлея выделения `CrudDataTable`). Бэкенд/таблица не тронуты
  (осталась собственная `useServerTable` + `AccessEntityDetailModal`).

Проверка: `bun run typecheck` не добавляет новых ошибок относительно baseline
(baseline красный из-за незакрытого долга авто-импортов, ROADMAP D6 — вне
объёма).

## Часть B — «Подписки по ролям» в группу «Доступ» ✅ СДЕЛАНО

- Пункт `role-subscription-rules` удалён из `dictionaryItems`
  (`src/modules/dictionaries/config.ts`).
- Добавлен в `accessItems` (`src/modules/access/config.ts`) как
  `subscriptions` → `/access/subscriptions`; автоматически появляется во
  вкладках `AccessNavigation` и в дереве «Доступ» сайдбара (`MainLayout.vue`).
- Новый роут `/access/subscriptions` → `AccessSubscriptionsPage.vue`
  (`src/modules/access/pages/`), рендерит `WorkflowCrudPage` с конфигом
  `crudModules['role-subscription-rules']` (`resource: 'user-types'`) и
  `AccessNavigation` в `#toolbar-extra`.
- `MainLayout.accessKeyToResource` — `subscriptions → 'user-types'` (то же
  право, что у ролей).

CRUD-модуль подписок (`endpoint /role_subscription_rules`) не менялся — только
переехало место в навигации.

---

## Часть C — Упрощение статусной модели (research + tests) 🔧 ПЛАН

Текущая модель (`src/core/status_codes.py`,
`.../domain/status_policy.py::ALLOWED_TRANSITIONS`, `docs/product/statuses.md`):

```
RESEARCH: draft → ordered → in_progress → completed;  draft/ordered → rejected;  completed → in_progress (reopen)
TEST:     queued → in_progress → completed;  queued/in_progress → rejected;  in_progress → queued (requeue)
```

### Предлагаемая целевая модель (рекомендация — подтвердить)

```
RESEARCH: in_progress → completed;  in_progress → rejected           (создаётся сразу в in_progress)
TEST:     in_progress → completed;  in_progress → rejected           (создаётся сразу в in_progress, редактируется на месте)
```

- **research**: убрать `draft` и `ordered`. `assign_research` создаёт research
  сразу в `in_progress` (или, мягче, оставить создание в `in_progress` при
  первом внесённом результате теста). Команды `research.confirm`/`research.start`
  удаляются из UI и API.
- **tests**: убрать `queued` и ручной «взять в работу» + `requeue`. Тест
  создаётся в `in_progress`, `completed` при внесении результата (`value`/`norm`),
  `rejected` — по причине.

### Затрагиваемые места

Backend:
- `src/core/status_codes.py` — константы RESEARCH/TEST.
- `.../domain/status_policy.py` — `ALLOWED_TRANSITIONS['research'|'tests']`.
- `.../infrastructure/repositories.py` — `assign_research` (стартовый статус),
  удалить/упростить `confirm_research`, `start_research`, `start_test`,
  `requeue_test`; каскад `_complete_parents_when_terminal` (не завязываться на
  `ordered`/`queued`); побочный эффект `start_research` (перевод образца
  `registered→in_progress` и направления в `in_progress`) перенести на момент
  `assign_research`/регистрации (иначе `in_progress → analyzed` каскад
  сломается — см. lab-doctor.flow §4 предусловие).
- `src/api/v1/.../router.py` — убрать эндпоинты `research/{id}/confirm|start`,
  `tests/{id}/start|requeue` (или оставить как no-op на переходный период).
- Миграция статус-таблиц: удалить строки `research_statuses.code in (draft, ordered)`
  и `test_statuses.code = queued`; **сид/бэкофилл** существующих строк
  (`draft/ordered → in_progress`, `queued → in_progress`). Alembic
  `revision --autogenerate` + ручной data-migration.
- `scripts/seed_test_data.py` — если сидит research/tests в старых статусах.

Frontend:
- `src/shared/config/workflow-commands.ts` — убрать команды `research.confirm`,
  `research.start`, `tests.start`, `tests.requeue`; статус-триггеры оставшихся
  команд (`tests.complete`, `*.reject`) — на `in_progress`.
- `src/shared/domain/status-timeline.ts` и бейджи — обновить наборы статусов.
- SDK-regen (`bun run sdk:generate`) + `typecheck`.

Документация: `docs/product/statuses.md`, оба flow-дока, глоссарий.

### Влияние на e2e
`lab-doctor-lifecycle.spec.ts` завязан на `research.confirm/start`,
`tests.start/requeue` и бейджи «Запланировано»/«Черновик». Спеку и хелперы
(`support/api.ts`, `support/nav.ts`) переписать под новую модель. Это делает
**Sonnet-субагент** после реализации Части C (см. Часть G).

---

## Часть D — Авто-назначение целей исследования при регистрации 🔧 ПЛАН

Сейчас регистрация, наоборот, **требует** предварительного `assign_research`
на каждом образце (`_ensure_direction_ready_for_registration`,
`repositories.py`) — иначе `409 direction_missing_research_assignments`.
Задача — перевернуть: цели назначаются **автоматически**.

### Рекомендация (подтвердить) — по типу образца

1. Новый справочный маппинг `sample_type_id → [research_goal_id]`
   (таблица `sample_type_research_goals` или JSON-конфиг + сид). Начальник
   лаборатории ведёт его в своей лаборатории (ROADMAP C3).
2. В `register_direction` (`repositories.py`): для каждого образца без
   research — авто-создать research по целям его `sample_type` (переиспользуя
   `assign_research`, который уже плодит `tests` по индикаторам цели).
3. Убрать предусловие `direction_missing_research_assignments`; оставить
   проверки «есть образцы» и «у образца заполнен тип» (тип нужен для маппинга).
4. Ручной `assign_research` остаётся доступным (добавить/скорректировать цели).

Альтернативы — см. «Открытые решения» (по отметкам импорта BAK/TH/…; одна
дефолтная цель-заглушка).

Frontend: шаг «назначить исследование» в мастере регистратора становится
опциональным/информационным; регистрация показывает, какие цели назначились.

---

## Часть E — Выпуск образца из лаборатории + протокол на образцы/направление 🔧 ПЛАН

- **Выпуск образца** = `close` (`analyzed → completed`, вердикт), уже есть
  (`POST /samples/{id}/close`, `repositories.py::close_sample`; ROADMAP C2/C3).
  Уточнить роль-инициатора (ВЛ и/или НЛ) на UI.
- **Протокол на образцы или направление** — уже поддержано:
  `POST /protocols` принимает список `sample_ids` (один или много, все
  `completed`/`rejected`), UI-кнопка «Создать протокол» на `/samples`
  (`registrator.flow.md` §16). «На направление целиком» = выделить все его
  образцы; «на часть» = подмножество.
- Что добавить: удобный вход «протокол на направление» прямо из окна Части F
  (кнопка на группе-направлении, предзаполняющая `sample_ids` всеми
  выпущенными образцами направления). Опционально — группировка образцов по
  направлению в рендере протокола (`protocol_report_repository.py`,
  сейчас плоский список с колонкой «direction_no»).

---

## Часть F — Окно «Выпущенные образцы по направлениям» (регистратор) 🔧 ПЛАН = ROADMAP C1.4

Экран: выпущенные (`completed`) образцы, **сгруппированные по направлениям**,
со статусом остальных образцов направления. **Если все образцы направления
выпущены — направление подсвечивается жёлтым.** По группе — действие
«Создать протокол».

### Backend — read-проекция (рекомендуется вместо чат­ливой FE-агрегации)
Новый эндпоинт, напр. `GET /directions/released-samples` →
`[{ direction: {...}, released_count, total_count, all_released: bool,
samples: [{id, name, status, sample_type, protocol_id}] }]`. Агрегат по
направлению (выпущено/всего + флаг). Реализация — `infrastructure/repositories/`
(read-проекция, как `dashboard.py`). Пагинация/фильтр по филиалу.

### Frontend
- Новая страница `SamplesReleasedByDirectionPage.vue` (или вкладка на
  `/samples`), пункт меню у регистратора. Рендер — группы-направления
  (`UAccordion`/карточки), жёлтая подсветка при `all_released`,
  `data-telemetry` (ROADMAP A2.3).
- Кнопка «Создать протокол по направлению» → существующий `POST /protocols`
  с `sample_ids` выпущенных образцов группы (переиспользовать
  `create-protocol-from-selection` из `DictionaryCrudContent.vue`).
- SDK-regen после появления эндпоинта.

---

## Часть G — SDK, верификация, e2e + видео (Sonnet-субагент)

1. После Частей C–F: `cd frontend && bun run sdk:generate` + `bun run typecheck`.
2. `make be-test be-lint`, `bun run lint typecheck build`, `bun test tests/shared`.
3. **Sonnet-субагент** поднимает стек (Postgres → `make be-migrate be-seed-data
   be-dev`, `make fe-dev`) и гоняет Playwright **с видео**:
   `cd frontend && bun run test:e2e:video tests/e2e/lab-doctor-lifecycle.spec.ts`
   и спеки регистратора (`direction-lifecycle`, `sample-lifecycle`,
   `protocol`, `import`). Учётки: `registrator/registrator123`,
   `doctor/doctor123`. Артефакты `.webm` — в `test-results/`.
4. После правок модели статусов — обновить e2e-спеки/хелперы под новую модель
   (иначе упадут на снятых командах `confirm/start/requeue`).

---

## Открытые решения (нужно подтверждение владельца)

Реализованы предположения (interactive-опрос в сессии не открылся):
- **C.research**: убрать `ordered` (assign → in_progress → completed).
- **C.tests**: убрать `queued`/старт и `requeue` (создан → completed по
  результату; rejected остаётся).
- **D.авто-цели**: по типу образца (`sample_type → набор целей`), справочный
  маппинг.

Если владелец выберет иначе (research оставить; tests только без requeue;
авто-цели по отметкам импорта / одна дефолтная) — скорректировать Части C–D
до реализации миграций.

## Порядок и DoD

1. A, B (frontend) — **готово**, коммит/пуш этой ветки.
2. C (backend статусы) + миграция + SDK + обновление e2e.
3. D (авто-цели) + миграция маппинга + SDK.
4. E/F (выпуск/протокол/окно) + read-проекция + SDK + FE-страница.
5. G — Sonnet прогоняет e2e с видео для регистратора и ВЛ.

**DoD**: `make lint test build` зелёные; SDK синхронизирован; статус-модель
исследований/испытаний упрощена и отражена в `statuses.md` + flow-доках;
регистрация авто-назначает цели; окно выпущенных образцов с жёлтой подсветкой;
видео e2e регистратора и ВЛ записаны.
