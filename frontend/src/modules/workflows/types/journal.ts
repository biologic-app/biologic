// types/journal.ts
// Полная модель журнала с версионированием, историей заполнений и экспортом

// ─── Базовые типы полей ─────────────────────────────────────────────────────

// json-logic-правило поверх answers (условия, computed-поля, видимость).
export type JsonLogicRule = Record<string, unknown>

export type FieldType =
  | 'text' | 'number' | 'boolean' | 'select' | 'date' | 'textarea' // v1 (паритет)
  | 'dictionary' // v2: опции из справочников backend (рендер — US-005)
  | 'file' // v2: вложения workflow_attachments (рендер — US-005)
  | 'computed' // v2: вычисляемое, read-only (рендер — US-005)

export interface JournalFieldOption {
  label: string
  value: string | number | boolean
}

// Источник опций для type: 'dictionary' (ресурс catalogs API). См. schema-doc §4.
export interface DictionarySource {
  endpoint: string
  valueKey?: string // default 'id'
  labelKey?: string // default 'name'
  searchable?: boolean
  filters?: Record<string, string>
}

// Правила валидации поля (schema-doc §4). Исполнение — US-005.
export type ValidationRule =
  | { kind: 'min'; value: number; message?: string }
  | { kind: 'max'; value: number; message?: string }
  | { kind: 'regex'; pattern: string; message?: string }
  | { kind: 'maxSizeMb'; value: number; message?: string } // только file

export interface JournalField {
  id: string
  label: string
  type: FieldType
  required?: boolean
  options?: JournalFieldOption[]
  placeholder?: string
  description?: string
  // v2-слоты. Здесь — только контракт типов; рендер расширенных типов — US-005.
  source?: DictionarySource // type: 'dictionary'
  expr?: JsonLogicRule // type: 'computed'
  accept?: string // type: 'file' (MIME/расширения)
  validation?: ValidationRule[]
  visibleWhen?: JsonLogicRule // скрытое поле не валидируется и не обязательно
}

// ─── Экран шага: грид 12 колонок со слотами (schema-doc §3) ──────────────────

export type Span = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12

// Повторяемая группа строк (пробы/измерения). Полноценный редактор — US-005.
export interface TableBlock {
  fieldId: string // ключ в answers: массив объектов-строк
  label: string
  columns: JournalField[] // колонки — обычные Field (без kind:'table')
  minRows?: number
  maxRows?: number
  addLabel?: string
}

// Разновидность блока грида (schema-doc §3): поле, секция-разделитель, таблица.
export type BlockKind = 'field' | 'section' | 'table'

export type Block =
  | { id: string; span: Span; kind: 'field'; field: JournalField }
  | { id: string; span: Span; kind: 'section'; title: string; description?: string }
  | { id: string; span: Span; kind: 'table'; table: TableBlock }

export interface Row {
  id: string
  blocks: Block[] // сумма span в ряду ≤ 12; излишек рендерер переносит на новый ряд
}

export interface Screen {
  rows: Row[]
}

// ─── Доменные действия (schema-doc §6). Исполнение — US-007 ──────────────────

export type AnswerRef =
  | { from: 'answer'; fieldId: string }
  | { from: 'const'; value: string | number | boolean }
  | { from: 'actor' } // текущий пользователь

export interface DomainAction {
  id: string
  label: string // «Завершить тест», показывается в раннере
  command: string // ключ реестра команд: 'tests.complete', …
  targetFrom: 'scope' | 'field' // откуда id целевой сущности
  targetField?: string // при targetFrom:'field' — id поля (обычно dictionary)
  argsMapping: Record<string, AnswerRef>
}

// ─── Ноды графа ─────────────────────────────────────────────────────────────

export interface JournalStepData {
  label: string
  description?: string
  role?: string
  fields: JournalField[] // v1: плоский список полей (сохранён для конструктора/паритета)
  screen?: Screen // v2: грид-экран (аддитивно; собирается конвертером §7)
  actions?: DomainAction[] // v2: доменные действия при завершении шага (§6)
}

export interface JournalConditionData {
  label: string
  rule: JsonLogicRule
}

// Цикл: повторяемый шаг. Врач добавляет произвольное число итераций
// (например, дополнительные тесты) и сам решает, когда выйти — сколько
// их будет, схема не фиксирует.
export interface JournalLoopData {
  label: string
  description?: string
  role?: string
  fields: JournalField[] // v1: поля итерации (сохранены для конструктора/паритета)
  screen?: Screen // v2: экран итерации (собирается конвертером §7)
  itemNoun?: string // как называть одну итерацию, напр. «тест»
}

export interface JournalNode {
  id: string
  type: 'start' | 'step' | 'condition' | 'loop' | 'end'
  position: { x: number; y: number }
  data: JournalStepData | JournalConditionData | JournalLoopData | { label: string }
}

export interface JournalEdge {
  id: string
  source: string
  target: string
  sourceHandle?: 'true' | 'false'
}

// ─── Схема (шаблон) журнала ─────────────────────────────────────────────────

export interface JournalSchema {
  id: string
  title: string
  formatVersion?: 2 // маркер формата v2; v1-схемы без поля конвертируются (§7)
  version: number
  description?: string
  createdAt?: string
  updatedAt?: string
  nodes: JournalNode[]
  edges: JournalEdge[]
}

// ─── Ответы и заполнение ────────────────────────────────────────────────────

export type JournalAnswerValue = string | number | boolean | null

// Одна строка table-блока: значения колонок по их fieldId (schema-doc §4).
export interface AnswerRow {
  [columnFieldId: string]: JournalAnswerValue
}

// Ссылка на вложение (type: 'file'). Хранится в answers массивом (schema-doc §4).
export interface AttachmentRef {
  attachmentId: string
  filename: string
  sizeBytes: number
}

export interface JournalAnswers {
  // Скаляр — примитивы/dictionary/computed; AnswerRow[] — table; AttachmentRef[] — file.
  [fieldId: string]: JournalAnswerValue | AnswerRow[] | AttachmentRef[]
}

// Комментарий к конкретной ноде в рамках одной записи (обсуждение шага)
export interface JournalComment {
  id: string
  nodeId: string
  author: string
  text: string
  createdAt: string
}

// Событие журнала изменений записи (аудит: кто и что сделал)
export type JournalActivityType =
  | 'created'
  | 'step_completed'
  | 'comment_added'
  | 'reopened'
  | 'completed'
  | 'reset'

export interface JournalActivityEvent {
  id: string
  type: JournalActivityType
  author: string
  at: string
  nodeId?: string
  label?: string // человекочитаемое (напр. название шага)
}

export interface JournalEntry {
  id: string
  schemaId: string
  schemaVersion: number
  // Область записи: id внешней сущности (например, исследования), к которой
  // привязано прохождение журнала. Пусто — глобальная запись шаблона.
  scope?: string
  title: string
  status: 'draft' | 'completed' | 'archived'
  answers: JournalAnswers
  // Итерации циклических нод: loopNodeId -> массив снимков ответов.
  loops?: Record<string, JournalAnswers[]>
  history: string[] // стек id пройденных step-нод
  currentNodeId: string
  createdBy?: string
  updatedBy?: string
  comments?: JournalComment[]
  activity?: JournalActivityEvent[]
  startedAt: string
  updatedAt: string
  completedAt?: string
  notes?: string
}

// ─── Версионирование ────────────────────────────────────────────────────────

export interface JournalTemplateVersion {
  schema: JournalSchema
  entries: JournalEntry[]
}

export interface JournalTemplate {
  id: string
  title: string
  versions: JournalTemplateVersion[]
  currentVersion: number
  createdAt: string
  updatedAt: string
}

// ─── Хранилище (localStorage) ───────────────────────────────────────────────

export interface JournalStorage {
  templates: JournalTemplate[]
  entries: JournalEntry[]
  lastTemplateId?: string
  lastEntryId?: string
}