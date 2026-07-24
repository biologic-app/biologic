# Workflow Schema v2 — спецификация формата

Статус: принята консенсусом плана (`.omc/plans/workflow-ui-engine-mvp-plan.md`, §2.2, §2.4).
Источник требований: `.omc/specs/deep-interview-workflow-ui-engine.md`.
Предшественник: формат v1 — `frontend/src/modules/workflows/types/journal.ts` (`JournalSchema`).

Схема v2 — единственный источник истины UI рабочего процесса: она описывает и **граф процесса**
(узлы/рёбра, условия, циклы), и **экран каждого шага** (грид 12 колонок со слотами), и
**доменные привязки** (чтение справочников, запись доменных сущностей через команды API).

---

## 1. Корневой контракт

```ts
interface WorkflowSchema {
  id: string
  title: string
  formatVersion: 2          // маркер формата; v1-схемы (без поля) конвертируются (§7)
  version: number           // номер версии внутри шаблона (существующая модель версий)
  description?: string
  createdAt?: string        // ISO-8601
  updatedAt?: string
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
}

interface WorkflowEdge {
  id: string
  source: string            // node id
  target: string            // node id
  sourceHandle?: 'true' | 'false'   // только для condition-узлов
}
```

## 2. Узлы графа

Типы узлов и семантика обхода **не меняются относительно v1** (паритет — приёмочный кейс
«Микробиология»):

```ts
type WorkflowNode =
  | { id: string; type: 'start';     position: XY; data: { label: string } }
  | { id: string; type: 'step';      position: XY; data: StepData }
  | { id: string; type: 'condition'; position: XY; data: ConditionData }
  | { id: string; type: 'loop';      position: XY; data: LoopData }
  | { id: string; type: 'end';       position: XY; data: { label: string } }

interface StepData {
  label: string
  description?: string
  role?: string             // информационное поле (R13: RBAC вне MVP, не ограничивает)
  screen: Screen            // v2: экран вместо плоского fields[]
  actions?: DomainAction[]  // v2: доменные действия при завершении шага (§6)
}

interface ConditionData {
  label: string
  rule: JsonLogicRule       // json-logic поверх answers; выход по sourceHandle 'true'/'false'
}

interface LoopData {
  label: string
  description?: string
  role?: string
  screen: Screen            // v2: поля итерации тоже экран
  itemNoun?: string         // «проба», «измерение» — подпись итерации
}
```

Обход: `start` → по рёбрам; `condition` вычисляет `rule` через `json-logic-js` над текущими
`answers` и идёт по ребру с соответствующим `sourceHandle`; `loop` накапливает массив
снапшотов итераций; `end` завершает прохождение. Возврат назад (`back`) — по `history`.

## 3. Экран шага: грид со слотами

Экран — вертикальный список рядов; ряд — грид из 12 колонок; блок занимает `span` колонок.
Никакого свободного позиционирования (решение R2/R11): порядок задаётся порядком
`rows[]`/`blocks[]`, ширина — `span`.

```ts
interface Screen { rows: Row[] }

interface Row {
  id: string
  blocks: Block[]           // сумма span в ряду ≤ 12; рендерер переносит излишек на новый ряд
}

type Block =
  | { id: string; span: Span; kind: 'field';   field: Field }
  | { id: string; span: Span; kind: 'section'; title: string; description?: string }
  | { id: string; span: Span; kind: 'table';   table: TableBlock }

type Span = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12

interface TableBlock {                 // повторяемая группа: строки проб/измерений
  fieldId: string                      // ключ в answers: массив объектов-строк
  label: string
  columns: Field[]                     // колонки — обычные Field (кроме kind:'table')
  minRows?: number
  maxRows?: number
  addLabel?: string                    // подпись кнопки «добавить строку»
}
```

Рендер в Nuxt UI: ряд — CSS grid `grid-cols-12`; блок — `col-span-{span}`; `section` —
заголовок-разделитель (`USeparator` + текст); `field` — `UFormField` с контролом по типу (§4);
`table` — `UTable`-подобная редактируемая таблица с контролами в ячейках.

## 4. Поля

```ts
type FieldType =
  | 'text' | 'number' | 'boolean' | 'select' | 'date' | 'textarea'   // v1 (паритет)
  | 'dictionary'   // v2: опции из справочников backend
  | 'file'         // v2: вложения (workflow_attachments API)
  | 'computed'     // v2: вычисляемое, read-only

interface Field {
  id: string                   // ключ ответа в answers
  label: string
  type: FieldType
  required?: boolean
  placeholder?: string
  description?: string
  options?: { label: string; value: string }[]   // для type: 'select'
  source?: DictionarySource                      // для type: 'dictionary'
  expr?: JsonLogicRule                           // для type: 'computed'
  accept?: string                                // для type: 'file' (MIME/расширения)
  validation?: ValidationRule[]
  visibleWhen?: JsonLogicRule                    // скрытое поле не валидируется и не обязательно
}

interface DictionarySource {
  endpoint: string             // ресурс catalogs API, напр. 'employees', 'equipment'
  valueKey?: string            // default 'id'
  labelKey?: string            // default 'name'
  searchable?: boolean         // USelectMenu с поиском
  filters?: Record<string, string>
}

type ValidationRule =
  | { kind: 'min'; value: number; message?: string }        // number | длина строки
  | { kind: 'max'; value: number; message?: string }
  | { kind: 'regex'; pattern: string; message?: string }
  | { kind: 'maxSizeMb'; value: number; message?: string }  // только file
```

Маппинг на Nuxt UI (эволюция `JournalRunner.vue:325-352`): `text→UInput`, `textarea→UTextarea`,
`number→UInput[type=number]`, `boolean→USwitch`, `select→USelect`, `date→UInputDate`,
`dictionary→USelectMenu` (+загрузка через SDK), `file→UFileUpload`, `computed→read-only UInput`.

### Ответы

```ts
type AnswerValue = string | number | boolean | null
type Answers = Record<string, AnswerValue | AnswerRow[] | AttachmentRef[]>
interface AnswerRow { [columnFieldId: string]: AnswerValue }   // строка table-блока
interface AttachmentRef { attachmentId: string; filename: string; sizeBytes: number }
```

`computed`-поля пересчитываются движком при каждом изменении `answers` и записываются в
`answers` (доступны условиям, действиям и последующим шагам). Циклические зависимости
`computed`-полей — ошибка валидации схемы.

## 5. Валидация схемы (backend)

`POST /workflow-templates/{id}/versions` принимает схему только после Pydantic-валидации:
- `formatVersion == 2`; ровно один `start` и ≥1 `end`; все `edges` ссылаются на существующие узлы;
- у `condition` — исходящие рёбра `true` и `false`; граф достижим от `start` до какого-либо `end`;
- `id` полей уникальны в пределах схемы; `table.columns` не содержат `kind:'table'` (без вложенных таблиц в MVP);
- `computed.expr` не образуют циклов; `span` ∈ 1..12.

Версии иммутабельны: правки текущего черновика идут через `updateCurrentSchema`-эквивалент
(PATCH последней черновой версии), фиксация — команда `versions`.

## 6. Доменные действия и протокол `execute-step`

```ts
interface DomainAction {
  id: string
  label: string                       // «Завершить тест», показывается в раннере
  command: string                     // ключ реестра команд: 'tests.complete', 'samples.reject', …
  targetFrom: 'scope' | 'field'       // откуда id целевой сущности
  targetField?: string                // при targetFrom:'field' — id поля (обычно dictionary)
  argsMapping: Record<string, AnswerRef>   // аргументы команды из ответов
}

type AnswerRef =
  | { from: 'answer'; fieldId: string }
  | { from: 'const'; value: string | number | boolean }
  | { from: 'actor' }                 // текущий пользователь
```

Реестр команд (frontend, по образцу `shared/domain/workflow-commands.ts`) отображает
`command` на SDK-вызов и его précondition-статусы. **Исполнение — только сервером**:

```
POST /api/v1/workflow-runs/{id}/execute-step
{ node_id, attempt, actions: [{ action_id, command, resolved_args }] }
```

Сервер в одном UoW: идемпотентный страж `workflow_step_executions`
UNIQUE(run_id, node_id, attempt) → повтор возвращает `already_applied` с сохранённым
результатом; валидация переходов `ensure_allowed_transition` (быстрый 409 до мутаций —
намеренный pre-check, авторитетная валидация остаётся в доменном сервисе); мутации через
UoW-инъектируемые команды `WorkflowCommandService`; `change_log.workflow_run_id` — корреляция;
событие в `workflow_run_events`. Все `actions[]` шага атомарны (rollback целиком).

**Семантика `attempt`:** при прозрачном сетевом ретрае клиент пересылает **тот же** `attempt`;
инкремент — только при осознанном повторном запуске пользователем. Раннер различает три
исхода: `applied` / `already_applied` (ретрай, без ошибки) / problem-details 409 (переход
запрещён политикой — показать причину).

**Preview** (R4/R10): `execute-step` не вызывается никогда; действия перехватываются в
`PreviewActionLog` («что было бы вызвано»); чтение (`dictionary` и пр.) — реальное.

## 7. Конвертер v1 → v2

Детерминированные правила (unit-тесты на 3 демо-схемах prototype):
1. `formatVersion` отсутствует → схема v1.
2. `step.data.fields[]` → `screen.rows = fields.map(f => ({ id: rowId(f), blocks: [{ id: blockId(f), span: 12, kind: 'field', field: mapField(f) }] }))`.
3. `loop.data.fields[]` — аналогично; `itemNoun` сохраняется.
4. `mapField`: типы v1 переходят 1:1; `options` сохраняются; новых свойств не появляется.
5. `condition.rule`, `edges`, `position`, `history`-семантика — без изменений.
6. Ответы существующих записей (`JournalEntry.answers`, `loops`) совместимы без преобразования
   (ключи полей не меняются).

## 8. Примеры: четыре эталона (приёмка R12)

Компактные фрагменты; полные сиды — `make be-seed-data` (Фаза 8 плана).

### 8.1 Лабораторный с результатами тестов (двусторонняя интеграция)

```jsonc
{ "formatVersion": 2, "title": "Выполнение теста исследования",
  "nodes": [
    { "id": "n1", "type": "start", "data": { "label": "Начало" } },
    { "id": "n2", "type": "step", "data": { "label": "Выбор теста", "screen": { "rows": [
        { "id": "r1", "blocks": [ { "id": "b1", "span": 12, "kind": "field", "field": {
          "id": "test_id", "label": "Тест (в работе)", "type": "dictionary", "required": true,
          "source": { "endpoint": "tests", "labelKey": "name", "filters": { "status": "in_progress" } } } } ] } ] } } },
    { "id": "n3", "type": "step", "data": { "label": "Результат", "screen": { "rows": [
        { "id": "r2", "blocks": [
          { "id": "b2", "span": 6, "kind": "field", "field": { "id": "result_value", "label": "Значение", "type": "number", "required": true,
            "validation": [ { "kind": "min", "value": 0 } ] } },
          { "id": "b3", "span": 6, "kind": "field", "field": { "id": "verdict", "label": "Вердикт", "type": "select", "required": true,
            "options": [ { "label": "Соответствует", "value": "pass" }, { "label": "Не соответствует", "value": "fail" } ] } } ] } ] },
      "actions": [ { "id": "a1", "label": "Завершить тест", "command": "tests.complete",
        "targetFrom": "field", "targetField": "test_id",
        "argsMapping": { "result": { "from": "answer", "fieldId": "result_value" },
                          "verdict": { "from": "answer", "fieldId": "verdict" },
                          "actor_id": { "from": "actor" } } } ] } },
    { "id": "n4", "type": "end", "data": { "label": "Готово" } } ],
  "edges": [ { "id": "e1", "source": "n1", "target": "n2" },
             { "id": "e2", "source": "n2", "target": "n3" },
             { "id": "e3", "source": "n3", "target": "n4" } ] }
```
Предусловие сида: целевой тест переведён в `in_progress` (политика `tests`: только
`in_progress→completed`).

### 8.2 Журнал пожарной безопасности (универсальность, без домена)

```jsonc
{ "formatVersion": 2, "title": "Отчёт о пожарной безопасности",
  "nodes": [
    { "id": "n1", "type": "start", "data": { "label": "Начало" } },
    { "id": "n2", "type": "step", "data": { "label": "Осмотр помещений", "screen": { "rows": [
        { "id": "r1", "blocks": [ { "id": "s1", "span": 12, "kind": "section", "title": "Общие сведения" } ] },
        { "id": "r2", "blocks": [
          { "id": "b1", "span": 6, "kind": "field", "field": { "id": "inspector", "label": "Проверяющий", "type": "dictionary",
            "required": true, "source": { "endpoint": "employees", "labelKey": "full_name", "searchable": true } } },
          { "id": "b2", "span": 6, "kind": "field", "field": { "id": "date", "label": "Дата осмотра", "type": "date", "required": true } } ] },
        { "id": "r3", "blocks": [ { "id": "t1", "span": 12, "kind": "table", "table": {
            "fieldId": "rooms", "label": "Помещения", "minRows": 1, "addLabel": "Добавить помещение",
            "columns": [
              { "id": "room", "label": "Помещение", "type": "text", "required": true },
              { "id": "extinguisher_ok", "label": "Огнетушитель", "type": "boolean" },
              { "id": "note", "label": "Замечание", "type": "text" } ] } } ] },
        { "id": "r4", "blocks": [ { "id": "b3", "span": 12, "kind": "field", "field": {
            "id": "photo", "label": "Фото нарушений", "type": "file", "accept": "image/*",
            "validation": [ { "kind": "maxSizeMb", "value": 10 } ] } } ] } ] } } },
    { "id": "n3", "type": "condition", "data": { "label": "Есть нарушения?",
        "rule": { "some": [ { "var": "rooms" }, { "==": [ { "var": "extinguisher_ok" }, false ] } ] } } },
    { "id": "n4", "type": "step", "data": { "label": "План устранения", "screen": { "rows": [
        { "id": "r5", "blocks": [ { "id": "b4", "span": 12, "kind": "field", "field": {
            "id": "plan", "label": "Мероприятия", "type": "textarea", "required": true } } ] } ] } } },
    { "id": "n5", "type": "end", "data": { "label": "Отчёт готов" } } ],
  "edges": [ { "id": "e1", "source": "n1", "target": "n2" },
             { "id": "e2", "source": "n2", "target": "n3" },
             { "id": "e3", "source": "n3", "sourceHandle": "true", "target": "n4" },
             { "id": "e4", "source": "n3", "sourceHandle": "false", "target": "n5" },
             { "id": "e5", "source": "n4", "target": "n5" } ] }
```

### 8.3 Микробиологическое исследование (паритет v1)

Получается **конвертером §7** из `data/microbiology-study.ts` без ручных правок: каждый
`fields[]` шага/цикла становится рядами span-12; циклы («посевы»), условие «контроль бульона»,
select/boolean/date-поля сохраняются 1:1. Эталон фиксирует: конверсия + прохождение дают тот
же результат (answers/loops/history), что и v1-движок.

### 8.4 Эквивалент импорта направлений (стресс-тест выразительности)

Документ-эталон (процесс остаётся захардкоженным — non-goal R8): загрузка файла (`file` +
`accept: .xls,.xlsx`), шаг маппинга колонок (`table` с колонками `dictionary`), condition
«есть ошибки валидации?» (json-logic по `computed`-полю счётчика ошибок), цикл по
проблемным строкам (`loop` + `screen` с полями исправления), финальный шаг с `actions:
[{ command: 'directions.import', … }]`. Полная схема — приложение к отчёту Фазы 1;
демонстрирует: file + table + dictionary + computed + condition + loop + action в одной схеме.

---

## Приложение А. Соответствие решениям консенсуса

| Решение | Раздел |
|---|---|
| Двухуровневая схема: поля + layout (R1, R2) | §3 |
| MVP-библиотека полей (R6) | §4 |
| Доменные действия двусторонние, исполнение сервером (R9 + Architect) | §6 |
| Идемпотентность/атомарность/attempt (Architect/Critic) | §6 |
| Preview: чтение реальное, запись мок (R4/R10) | §6 |
| Конвертер вместо двух форматов (принцип 4 плана) | §7 |
| role — информационное (R13) | §2 |
