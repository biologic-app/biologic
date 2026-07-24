# Редизайн визуализации воркфлоу (журналов): master-detail + top-down канвас

> **Статус (2026-07-23):** лайаут утверждён на статичном макете; план утверждён пользователем.
> Дизайн-док в серии `docs/architecture/2026-07-22-workflow-*`. Реализация ещё не начата.
> См. также: `2026-07-22-workflow-ui-engine-overview.md`, `2026-07-22-workflow-schema-v2.md`,
> `2026-07-22-workflow-engine-adopt-vs-build.md`, `docs/research/2026-07-22-workflow-render-engines.md`.

## Context

Страница `/workflows` («Рабочие процессы») сейчас — плоская таблица, а сам граф
заперт в модалке (`WorkflowDetailModal` → `JournalBuilder`), рисуется **слева-направо**, ноды
невзрачны, инфо по ноде редактируется в узкой inline-колонке. Цель — уровень референсов
(n8n-подобные ноды, вертикальный поток): **список журналов слева + живой канвас справа**, ноды
**сверху-вниз**, аккуратные карточки-ноды, контекст-меню по ноде, и **сайдбар-оверлей** с
инфо/редактором ноды.

Фундамент уже есть и переиспользуется. **Vue Flow 1.48.2 установлен**, есть 5 кастомных нод и
общая дизайн-система на токенах Nuxt UI (`workflow-nodes.css`). Модель графа
(`types/journal.ts`) целиком на фронте и **непрозрачна для бэкенда** (JSONB round-trip) —
значит менять форму/раскладку можно свободно, **без изменений backend и без регенерации SDK**.
Это апгрейд + переезд, не переписывание.

Решения пользователя: **полный master-detail** (канвас из модалки на страницу); авто-раскладка =
**кнопка «Упорядочить» + сохраняемый ручной drag**; инфо ноды = **`USlideover` (оверлей справа)**;
плюс **заметная кнопка «Тестовый прогон» (Preview)** на странице воркфлоу.

## Итог по развилкам (зафиксировано)
- **Объём:** канвас переезжает из модалки на страницу; таблица → компактный список слева.
- **Раскладка:** dagre `rankdir: TB` по кнопке; ручные позиции нод сохраняются как сейчас.
- **Панель ноды:** `USlideover` справа по клику на ноду.
- **Тестовый прогон:** отдельная кнопка → `WorkflowPreview` (песочница, без записи в БД).

---

## Изменения

### 1. Зависимость: dagre
- `frontend/package.json`: добавить `@dagrejs/dagre` (движок из официального примера Vue Flow;
  `dagre` сейчас НЕ установлен). Ставить через `bun add @dagrejs/dagre` (инструментарий FE — только bun).

### 2. Авто-раскладка — новый композабл
- Создать `frontend/src/modules/workflows/composables/useWorkflowLayout.ts` по эталону Vue Flow:
  ```ts
  import dagre from '@dagrejs/dagre'
  import { Position, useVueFlow } from '@vue-flow/core'
  // layout(nodes, edges, 'TB') → g.setGraph({ rankdir:'TB', ranksep:60, nodesep:40 })
  // для каждой ноды g.setNode(id, { width: findNode(id).dimensions.width||260, height: ...||96 })
  // dagre.layout(g); вернуть nodes с position=g.node(id) и
  // targetPosition: Position.Top, sourcePosition: Position.Bottom
  ```
- Учесть condition-ноду с двумя source-хэндлами (`true`/`false`): в dagre это один узел с двумя
  исходящими рёбрами — раскладка корректна из коробки; хэндлы просто на нижней грани.

### 3. Ориентация сверху-вниз — ноды и хэндлы
Во всех 5 нодах (`components/nodes/Journal{Start,Step,Condition,Loop,End}Node.vue`) сменить хэндлы:
- `target`: `Position.Left` → `Position.Top`; `source`: `Position.Right` → `Position.Bottom`.
- `JournalConditionNode.vue`: два source-хэндла `true`/`false` перенести с правой грани на **нижнюю**
  (side-by-side: true слева, false справа). Переписать `:deep(.wf-handle--true/false)` на
  `left: 32% / 68%; bottom: -6px; top:auto`. Бейджи «Да»/«Нет» — в горизонтальный ряд снизу.
- `workflow-nodes.css`: правила `.vue-flow__handle` не привязаны к стороне — оставить; при желании
  чуть увеличить hit-area. Рёбра остаются `smoothstep` (авто-роутинг → рисует вертикально).
- `JournalBuilder.nextPosition()`: раскладывать новые ноды **в столбец** (x фикс, y += 160), а не 4 колонки.

### 4. Канвас без inline-инспектора → инфо ноды в `USlideover`
Файл `frontend/src/modules/workflows/components/JournalBuilder.vue` (остаётся хостом канваса,
минимальный риск — вся логика save/version/autosave/`activeScreen`/`activeActions` не трогается):
- Убрать 2-колоночный grid и `<aside class="journal-builder__inspector">`.
- Канвас `.journal-builder__canvas` растягивается на всю область панели.
- Содержимое бывшего `<aside>` (мета-форма узла + `ScreenEditor` + `StepActionsEditor` + `RuleBuilder`)
  **перенести внутрь `USlideover`** (новый компонент `WorkflowNodeSlideover.vue` ИЛИ inline-`USlideover`
  в билдере). `@node-click` → `slideoverOpen = true` + `selectedNodeId`. Двусторонняя правка
  (`selectedNode.data`, `activeScreen`, `activeActions`) сохраняется как есть — это move, не rewrite.
- В тулбар канваса (`<Panel position="top-left">`) добавить кнопку **«Упорядочить»**
  (`i-lucide-network`) → `layout()` из `useWorkflowLayout`, затем `fitView()` (есть в `useVueFlow`).
  Позиции персистятся существующим `watch([nodes,edges], deep)` → `saveCurrent()`.

### 5. Контекст-меню по ноде
- На `<VueFlow>` повесить `@node-context-menu` (событие есть в 1.48.2) → открыть плавающее меню,
  **переиспользуя `frontend/src/shared/ui/RowContextMenu.vue`** (тот же паттерн, что для строк таблицы:
  `:x/:y/:items/v-model:open`). Пункты: Открыть (slideover), Дублировать, Создать связанную, Удалить.
- Опционально: видимая «⋯» в шапке ноды на hover (через `provide/inject` обработчика из билдера в ноды).
  Рекомендую начать с right-click — он покрывает сценарий без изменения сигнатуры нод.

### 6. Полировка нод
- `frontend/src/app/styles/workflow-nodes.css` + шаблоны нод: усилить шапку (иконка+тайтл+«⋯»),
  ключ→значение в теле, аккуратные тени/радиусы. Всё на существующих `--ui-*`/`--wf-accent` токенах,
  тема (light/dark) продолжает работать. Это в основном CSS + мелкие правки шаблонов.

### 7. Страница → master-detail
`frontend/src/pages/WorkflowsPage.vue` перестроить в **два соседних `UDashboardPanel`** внутри
существующего app-`UDashboardGroup` (страница уже рендерит `UDashboardPanel` + `UDashboardSidebarCollapse`,
т.е. группа/сайдбар приложения уже есть — менять оболочку не нужно). Паттерн — из dashboard-референса Nuxt UI:
- **Левая панель** `id="workflows-list"` `resizable` — компактный список журналов (не таблица):
  `UDashboardNavbar` (title + кнопка «Новый процесс») + `UInput` поиск + вертикальный список
  `listItems` (уже есть `DetailListItem[]`), подсветка выбранного, per-item контекст-меню
  (Открыть/Переименовать/Удалить — переиспользовать существующие `openRename/openDelete/rowActions`).
  Клик по элементу → `selectedTemplateId`.
- **Правая панель** `id="workflows-detail"` `class="hidden lg:flex"` — навбар с названием воркфлоу
  и **заметной кнопкой «Тестовый прогон» (Preview)** (см. §7a) + `[Упорядочить] [Новая версия]`.
  Ниже — канвас как основной вид, а вторичные виды (`Запуск`, `Карточка`) — сегментированный
  `UTabs` **Схема / Запуск / Карточка**:
  - *Схема* (по умолчанию) → `<JournalBuilder v-model="builderSchema" :template-id>` (канвас).
  - *Запуск* → существующий `JournalRunner` (боевые записи, пишет на сервер).
  - *Карточка* → существующие `EntityFieldGrid` + `UTimeline` версий (перенести из модалки).
- **Ретайр модалки:** содержимое `WorkflowDetailModal.vue` (card/preview/run tabs) переезжает в правую
  панель; сам `WorkflowDetailModal` и `EntityDetailModalShell`-обёртка на этой странице больше не нужны.
  Логику загрузки полного шаблона (`watch(detailId)`→`getTemplate`), `onVersionSaved`, create/rename/delete
  оставить в странице (переиспользовать).
- **Что упрощается (таблица→список):** bulk-select, column-visibility и filter-modal — фичи таблицы;
  в списке они не нужны и убираются. Останутся поиск + создание + удаление/переименование по контекст-меню.
  (Если нужны фильтры в списке — лёгкий доп.шаг, не в этой итерации.)

### 7a. Кнопка «Тестовый прогон» (Preview)
`WorkflowPreview.vue` **уже является тестовым прогоном** (US-008): гоняет **черновую, даже
несохранённую** схему in-memory, **ничего не пишет** в БД (движок без `onSave`), доменные действия
перехватывает в журнал «что было бы вызвано» (без `execute-step`), справочники читает реально,
плюс read-only граф с подсветкой пройденного маршрута. Его надо вынести в **заметную кнопку**, а
не во вкладку.
- В навбаре правой панели — кнопка **«Тестовый прогон»** (`i-lucide-flask-conical`, `color="primary"`
  `variant="soft"`), доступная всегда, когда открыт воркфлоу.
- Клик → большой оверлей (`UModal` size `xl`/`full` **или** широкий `USlideover`) с
  `<WorkflowPreview :schema="builderSchema" />`. Кормим **живой черновой схемой из редактора**:
  `builderSchema` на странице синхронизируется с канвасом (autosave `JournalBuilder`
  `saveCurrent()` → `emit('update:modelValue')`), поэтому прогон идёт по актуальным нодам/рёбрам,
  включая несохранённые правки — ровно то, для чего Preview спроектирован.
- Изоляция: `:key` оверлея = хэш/`updatedAt` схемы, чтобы при повторном открытии движок стартовал
  с чистого состояния на текущей схеме.
- `JournalRunner` (боевой прогон) остаётся отдельно во вкладке «Запуск» — это НЕ тестовый прогон
  (создаёт записи и шлёт на сервер); не путать с кнопкой Preview.

### 8. Роутинг (опционально, рекомендую)
- `frontend/src/app/router/routes.ts`: добавить `path: '/workflows/:id?'` чтобы выбор воркфлоу
  отражался в URL (deep-link/refresh). Небольшая правка; можно отложить.

### 9. i18n
- `frontend/src/shared/i18n/messages.ts`: добавить ключи `workflows.canvas.autoLayout` («Упорядочить»),
  заголовки слайдовера, лейбл списка. Табы (`detail.tabCard/tabBuilder/tabPreview/tabRun`) уже есть.

---

## Что переиспользуем (не пишем заново)
- Vue Flow 1.48.2 (`@vue-flow/core`, `@vue-flow/background`, `@vue-flow/controls`) — уже стоит.
- 5 нод-компонентов + `frontend/src/app/styles/workflow-nodes.css` (токены Nuxt UI).
- Инспектор-логику билдера: `activeScreen`, `activeActions`, `ScreenEditor`, `StepActionsEditor`,
  `RuleBuilder`, save/version/autosave, `ensureV2/toScreen/screenFields` из `engine/convert.ts`.
- `WorkflowPreview.vue`, `JournalRunner.vue`, `EntityFieldGrid.vue`, `RowContextMenu.vue`.
- API-адаптер `modules/workflows/api/workflows.api.ts` — без изменений (backend не трогаем).
- Эталон `useLayout` (dagre) из репозитория Vue Flow — как основа `useWorkflowLayout.ts`.

## Файлы
**Создать:** `modules/workflows/composables/useWorkflowLayout.ts`;
`modules/workflows/components/WorkflowNodeSlideover.vue` (либо inline-`USlideover` в билдере).
**Изменить:** `pages/WorkflowsPage.vue` (master-detail); `components/JournalBuilder.vue`
(канвас full-width + slideover + кнопка раскладки + node-context-menu); 5 `components/nodes/*.vue`
(хэндлы Top/Bottom, condition — снизу); `app/styles/workflow-nodes.css` (полировка); `package.json`
(`@dagrejs/dagre`); `shared/i18n/messages.ts` (ключи); опц. `app/router/routes.ts` (`:id?`).
**Ретайр:** использование `WorkflowDetailModal.vue` на странице (контент перенесён в правую панель).

## Verification (DoD)
- `cd frontend && bun run lint typecheck build` — зелёно (строгий TS + ESLint vue).
- `bun test tests/shared` — существующие тесты не падают.
- **Backend/SDK не трогаем** — граф непрозрачен для API, регенерация SDK не требуется.
- Ручной прогон (`bun run dev`, :5177 → `/workflows`):
  1. Слева список журналов, справа — канвас выбранного, ноды **сверху-вниз**, рёбра вертикальные.
  2. «Упорядочить» — dagre компактно раскладывает TB, `fitView` центрирует; ручной drag работает и сохраняется (перезагрузка сохраняет позиции).
  3. Клик по ноде → `USlideover` справа с инфо/редактором (шаг/цикл — экран+действия, условие — правило).
  4. Right-click по ноде → контекст-меню (Открыть/Дублировать/Удалить).
  5. **Кнопка «Тестовый прогон» (Preview)** в навбаре → оверлей с `WorkflowPreview` на живой
     черновой схеме: шаги проходятся, доменные действия НЕ уходят на сервер (журнал «что было бы
     вызвано»), маршрут подсвечивается, записи в БД не создаются. Несохранённая правка канваса
     видна в прогоне.
  6. Вкладки «Запуск»/«Карточка» в правой панели работают как раньше (боевой раннер пишет записи).
  7. Light/dark темы корректны (ноды на семантических токенах).
- Опц.: Playwright e2e (`bun run test:e2e`) — smoke по `/workflows` (выбор, клик ноды, слайдовер).

## Макет
Статичный HTML-макет утверждённого лайаута (master-detail + top-down ноды + слайдовер + кнопка
«Тестовый прогон»): artifact `c8d17bc0-0ca1-465c-a50c-1ed612e83b44`.
