// types/journal.ts
// Полная модель журнала с версионированием, историей заполнений и экспортом

// ─── Базовые типы полей ─────────────────────────────────────────────────────

export type FieldType = 'text' | 'number' | 'boolean' | 'select' | 'date' | 'textarea'

export interface JournalFieldOption {
  label: string
  value: string | number | boolean
}

export interface JournalField {
  id: string
  label: string
  type: FieldType
  required?: boolean
  options?: JournalFieldOption[]
  placeholder?: string
  description?: string
}

// ─── Ноды графа ─────────────────────────────────────────────────────────────

export interface JournalStepData {
  label: string
  description?: string
  role?: string
  fields: JournalField[]
}

export interface JournalConditionData {
  label: string
  rule: Record<string, unknown>
}

// Цикл: повторяемый шаг. Врач добавляет произвольное число итераций
// (например, дополнительные тесты) и сам решает, когда выйти — сколько
// их будет, схема не фиксирует.
export interface JournalLoopData {
  label: string
  description?: string
  role?: string
  fields: JournalField[]
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
  version: number
  description?: string
  createdAt?: string
  updatedAt?: string
  nodes: JournalNode[]
  edges: JournalEdge[]
}

// ─── Ответы и заполнение ────────────────────────────────────────────────────

export type JournalAnswerValue = string | number | boolean | null

export interface JournalAnswers {
  [fieldId: string]: JournalAnswerValue
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