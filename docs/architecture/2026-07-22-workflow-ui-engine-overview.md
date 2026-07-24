# Обзор: движок UI рабочих процессов (workflows)

Статус: реализовано (MVP, план `.omc/plans/workflow-ui-engine-mvp-plan.md`, US-001..009).
Связанные документы:
- ADR adopt-vs-build — `docs/architecture/2026-07-22-workflow-engine-adopt-vs-build.md`
- Спецификация формата (v2) — `docs/architecture/2026-07-22-workflow-schema-v2.md`
- Сравнение движков рендера — `docs/research/2026-07-22-workflow-render-engines.md`

Рабочий процесс («журнал») — это версионируемый шаблон, описывающий одновременно **граф
процесса** (шаги, условия, циклы), **экран каждого шага** (грид 12 колонок со слотами) и
**доменные привязки** (чтение справочников, запись доменных сущностей через команды API).
Формат схемы — v2, единый источник истины; его контракт — в schema-v2.md.

---

## 1. Frontend — `frontend/src/modules/workflows/`

> Исторически модуль назывался `journals`; после переезда в `workflows` внутренние
> идентификаторы (`JournalSchema`, `JournalNode`, `JournalRunner`, `useJournalEngine`, …)
> намеренно сохранены — это не путь и не публичный контракт, а имена типов/компонентов.
> Полное переименование идентификаторов — за рамками MVP (риск без выгоды).

- **`types/journal.ts`** — модель схемы v2: `JournalSchema`, узлы (`start/step/condition/loop/end`),
  `Screen`/`Row`/`Block`/`Field`, `TableBlock`, `DomainAction`, `JournalEntry` (прохождение).
- **`engine/`** — чистый TS (без Vue):
  - `convert.ts` — детерминированный конвертер v1 → v2 (`ensureV2`, `toScreen`, `screenFields`);
  - `screen.ts` / `fields.ts` — сбор полей экрана, валидация (`validateField`, `isVisible`, `maxSizeMb`);
  - `actions.ts` — резолвинг `DomainAction` в аргументы (`resolveActions`) и трекер попыток `execute-step`;
  - `action-commands.ts` — реестр доменных команд фронтенда (метки/précondition для UI);
  - `preview.ts` — сборка «перехваченного» вызова (`buildPreviewActionEntry`) для песочницы.
- **`composables/useJournalEngine.ts`** — состояние прохождения: `answers`, `history`, текущий
  шаг/экран/цикл, `goNext/goBack/addLoopItem`, авто-`persist` через `onSave` (fire-and-forget).
- **Компоненты**:
  - конструктор — `JournalBuilder.vue` (VueFlow-граф) + `ScreenEditor.vue`, `RuleBuilder.vue`,
    `StepActionsEditor.vue`, узлы `nodes/Journal*Node.vue`;
  - раннер — `JournalRunner.vue`, рендер экрана `WorkflowScreenRenderer.vue`, контрол поля
    `WorkflowFieldControl.vue` (все типы, включая dictionary/file/computed);
  - предпросмотр — `WorkflowPreview.vue` (RouteTrace + журнал перехвата);
  - карточка — `WorkflowDetailModal.vue` (вкладки Card / Builder / Preview / Run).
- **`api/workflows.api.ts`** — адаптер к backend (замена старому localStorage-хранилищу):
  шаблоны/версии/записи/комментарии/`execute-step`/вложения/справочники + `initDemoData`.
- **Точки входа**: страница реестра `src/pages/WorkflowsPage.vue` (маршрут `/workflows`,
  `nav.workflows`), вкладка исследования `components/ResearchWorkflowTab.vue`.

## 2. Backend

Модель хранения (таблицы, миграция `backend/migrations/versions/20260722_0031_workflows_module.py`):

| Таблица | Назначение |
|---|---|
| `workflow_templates` | шаблон + `current_version` |
| `workflow_schema_versions` | иммутабельные версии схемы (opaque JSONB-граф) |
| `workflow_runs` | прохождения (`answers`/`loops`/`history`/`current_node_id`, scope) |
| `workflow_run_events` | события записи (комментарии, шаги) |
| `workflow_step_executions` | идемпотентный страж `execute-step` — `UNIQUE(run_id, node_id, attempt)` |
| `workflow_attachments` | вложения полей `type:'file'` |

- **HTTP** — `backend/src/presentation/http/workflows/router.py` (`/api/v1`):
  CRUD `workflow-templates` (+ `/versions`, `/import`), CRUD `workflow-runs`
  (+ команды `/complete`, `/archive`, `/comments`, `/execute-step`), `workflow-attachments`.
- **Валидация схемы** — `backend/src/domain/workflows/schema.py` (Pydantic; правила §5 schema-v2:
  `formatVersion==2`, один `start` и ≥1 `end`, достижимость, уникальность id полей, `span∈1..12`,
  отсутствие циклов `computed`).
- **Доменные действия** — `backend/src/application/workflows/use_cases/execute_step.py`
  и реестр `command_registry.py` (сейчас: `tests.complete`, `tests.reject`). Один UoW:
  идемпотентный страж → быстрый pre-check перехода (`ensure_allowed_transition`, 409 до мутаций) →
  команды `WorkflowCommandService` → `change_log.workflow_run_id` → событие в `workflow_run_events`.
  Все `actions[]` шага атомарны (rollback целиком). Семантика `attempt`: прозрачный ретрай шлёт
  тот же `attempt` (`already_applied` без ошибки), инкремент — только при осознанном повторе.

## 3. Preview (песочница)

Preview проходит **черновую** (в т.ч. несохранённую) схему без записи: движок создаётся без
`onSave`, а доменные действия НЕ уходят в `execute-step` — вместо этого перехватываются в
журнал «что было бы вызвано». Чтение (dictionary и пр.) — реальное. За сессию preview: ноль
`createEntry`/`saveEntryProgress`/`executeStep`. RouteTrace — read-only VueFlow тех же узлов с
подсветкой пройденного маршрута. Приёмочная проверка — e2e `tests/e2e/workflows.spec.ts` (c).

## 4. Приёмочные эталоны (schema-v2 §8)

1. **Лабораторный** — `data/lab-test-result.ts` (сид): двусторонняя интеграция, `tests.complete`
   через `execute-step`.
2. **Пожарный журнал** — `data/fire-safety.ts` (сид): свободный отчёт БЕЗ домена — секция,
   dictionary, date, редактируемая таблица, file, условие по json-logic над строками таблицы.
3. **Микробиология** — `data/microbiology-study.ts` (сид): паритет v1 — циклы и условия
   (получается конвертером §7 без ручных правок).
4. **Импорт направлений** — документ-эталон (schema-v2 §8.4): процесс остаётся захардкоженным
   (non-goal), демонстрирует выразительность формата (file + table + dictionary + computed +
   condition + loop + action).

Регистрация демо: `initDemoData([...])` в `WorkflowsPage.vue` (идемпотентно — сидит только при
пустом реестре).

## 5. Тесты

- Unit (bun) — `frontend/tests/shared/workflows/` (`convert`, `screen`, `fields`, `actions`,
  `preview`, `engine-parity`).
- e2e (Playwright) — `frontend/tests/e2e/workflows.spec.ts`: пожарный журнал (a), лабораторный
  execute-step (b), preview-ноль-записей (c). Живой прогон требует поднятых app/API и справочных
  данных (`make be-seed-data`).
