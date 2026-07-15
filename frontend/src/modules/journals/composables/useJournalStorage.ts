// composables/useJournalStorage.ts
// Браузерное хранилище: localStorage + экспорт/импорт JSON

import type { JournalActivityEvent, JournalActivityType, JournalAnswers, JournalComment, JournalEntry, JournalSchema, JournalStorage, JournalTemplate } from '@/modules/journals/types/journal'

const STORAGE_KEY = 'journal-constructor-storage'

function loadStorage(): JournalStorage {
  if (typeof window === 'undefined') return { templates: [], entries: [] }
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { templates: [], entries: [] }
    return JSON.parse(raw) as JournalStorage
  } catch {
    return { templates: [], entries: [] }
  }
}

function saveStorage(data: JournalStorage) {
  if (typeof window === 'undefined') return
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
}

// ─── Утилиты ────────────────────────────────────────────────────────────────

function generateId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
}

// ─── Шаблоны (версионирование) ─────────────────────────────────────────────

export function getTemplates(): JournalTemplate[] {
  return loadStorage().templates
}

export function getTemplate(id: string): JournalTemplate | undefined {
  return loadStorage().templates.find((t) => t.id === id)
}

export function createTemplate(title: string, initialSchema: JournalSchema): JournalTemplate {
  const storage = loadStorage()
  const template: JournalTemplate = {
    id: generateId(),
    title,
    versions: [{ schema: initialSchema, entries: [] }],
    currentVersion: 1,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  }
  storage.templates.push(template)
  saveStorage(storage)
  return template
}

export function saveSchemaVersion(templateId: string, schema: JournalSchema): JournalTemplate {
  const storage = loadStorage()
  const template = storage.templates.find((t) => t.id === templateId)
  if (!template) throw new Error(`Template "${templateId}" not found`)

  const newVersion = template.versions.length + 1
  const newSchema: JournalSchema = {
    ...schema,
    id: template.id,
    version: newVersion,
    updatedAt: new Date().toISOString(),
  }

  template.versions.push({ schema: newSchema, entries: [] })
  template.currentVersion = newVersion
  template.updatedAt = new Date().toISOString()
  saveStorage(storage)
  return template
}

export function updateCurrentSchema(templateId: string, schema: JournalSchema): JournalTemplate {
  const storage = loadStorage()
  const template = storage.templates.find((t) => t.id === templateId)
  if (!template) throw new Error(`Template "${templateId}" not found`)

  const current = template.versions[template.currentVersion - 1]
  current.schema = {
    ...schema,
    id: template.id,
    version: template.currentVersion,
    updatedAt: new Date().toISOString(),
  }
  template.updatedAt = new Date().toISOString()
  saveStorage(storage)
  return template
}

export function getSchema(templateId: string, version?: number): JournalSchema | undefined {
  const template = getTemplate(templateId)
  if (!template) return undefined
  const v = version ?? template.currentVersion
  return template.versions[v - 1]?.schema
}

export function getSchemaVersions(templateId: string): JournalSchema[] {
  const template = getTemplate(templateId)
  if (!template) return []
  return template.versions.map((v) => v.schema)
}

export function deleteTemplate(templateId: string) {
  const storage = loadStorage()
  storage.templates = storage.templates.filter((t) => t.id !== templateId)
  storage.entries = storage.entries.filter((e) => e.schemaId !== templateId)
  saveStorage(storage)
}

export function renameTemplate(templateId: string, newTitle: string) {
  const storage = loadStorage()
  const template = storage.templates.find((t) => t.id === templateId)
  if (template) {
    template.title = newTitle
    template.updatedAt = new Date().toISOString()
    saveStorage(storage)
  }
}

// ─── Заполнения (entries) ───────────────────────────────────────────────────

export function getEntries(): JournalEntry[] {
  return loadStorage().entries
}

export function getEntriesForSchema(templateId: string, version?: number): JournalEntry[] {
  const storage = loadStorage()
  return storage.entries.filter((e) => {
    if (e.schemaId !== templateId) return false
    if (version !== undefined) return e.schemaVersion === version
    return true
  })
}

export function getEntry(entryId: string): JournalEntry | undefined {
  return loadStorage().entries.find((e) => e.id === entryId)
}

export function createEntry(templateId: string, version: number, title: string, author = ''): JournalEntry {
  const storage = loadStorage()
  const now = new Date().toISOString()
  const entry: JournalEntry = {
    id: generateId(),
    schemaId: templateId,
    schemaVersion: version,
    title,
    status: 'draft',
    answers: {},
    history: [],
    currentNodeId: 'start',
    createdBy: author,
    updatedBy: author,
    comments: [],
    activity: [
      { id: generateId(), type: 'created', author: author || 'Аноним', at: now },
    ],
    startedAt: now,
    updatedAt: now,
  }
  storage.entries.push(entry)
  storage.lastEntryId = entry.id
  saveStorage(storage)
  return entry
}

// Добавить комментарий к ноде в рамках записи + залогировать событие
export function addComment(entryId: string, nodeId: string, author: string, text: string, label?: string): JournalEntry {
  const storage = loadStorage()
  const entry = storage.entries.find((e) => e.id === entryId)
  if (!entry) throw new Error(`Entry "${entryId}" not found`)
  const now = new Date().toISOString()
  const comment: JournalComment = { id: generateId(), nodeId, author: author || 'Аноним', text, createdAt: now }
  entry.comments = [...(entry.comments ?? []), comment]
  entry.activity = [
    ...(entry.activity ?? []),
    { id: generateId(), type: 'comment_added', author: author || 'Аноним', at: now, nodeId, label },
  ]
  entry.updatedAt = now
  entry.updatedBy = author
  saveStorage(storage)
  return entry
}

// Записать произвольное событие в журнал изменений записи
export function logActivity(
  entryId: string,
  type: JournalActivityType,
  author: string,
  meta?: { nodeId?: string; label?: string },
): JournalEntry {
  const storage = loadStorage()
  const entry = storage.entries.find((e) => e.id === entryId)
  if (!entry) throw new Error(`Entry "${entryId}" not found`)
  const now = new Date().toISOString()
  const event: JournalActivityEvent = {
    id: generateId(),
    type,
    author: author || 'Аноним',
    at: now,
    ...(meta?.nodeId ? { nodeId: meta.nodeId } : {}),
    ...(meta?.label ? { label: meta.label } : {}),
  }
  entry.activity = [...(entry.activity ?? []), event]
  entry.updatedAt = now
  entry.updatedBy = author
  saveStorage(storage)
  return entry
}

export function updateEntry(entryId: string, patch: Partial<JournalEntry>): JournalEntry {
  const storage = loadStorage()
  const entry = storage.entries.find((e) => e.id === entryId)
  if (!entry) throw new Error(`Entry "${entryId}" not found`)

  Object.assign(entry, patch, { updatedAt: new Date().toISOString() })
  saveStorage(storage)
  return entry
}

export function saveEntryProgress(
  entryId: string,
  answers: JournalAnswers,
  history: string[],
  currentNodeId: string,
  loops?: Record<string, JournalAnswers[]>,
  updatedBy?: string,
): JournalEntry {
  return updateEntry(entryId, {
    answers,
    history,
    currentNodeId,
    ...(loops ? { loops } : {}),
    ...(updatedBy !== undefined ? { updatedBy } : {}),
    status: currentNodeId === 'end' ? 'completed' : 'draft',
    ...(currentNodeId === 'end' ? { completedAt: new Date().toISOString() } : {}),
  })
}

export function deleteEntry(entryId: string) {
  const storage = loadStorage()
  storage.entries = storage.entries.filter((e) => e.id !== entryId)
  saveStorage(storage)
}

// ─── Экспорт / Импорт ───────────────────────────────────────────────────────

export function exportAllData(): string {
  return JSON.stringify(loadStorage(), null, 2)
}

export function exportTemplate(templateId: string): string {
  const template = getTemplate(templateId)
  if (!template) throw new Error('Template not found')
  return JSON.stringify(template, null, 2)
}

export function exportEntry(entryId: string): string {
  const entry = getEntry(entryId)
  if (!entry) throw new Error('Entry not found')
  const template = getTemplate(entry.schemaId)
  return JSON.stringify({ entry, schema: template?.versions[entry.schemaVersion - 1]?.schema }, null, 2)
}

export function importData(json: string): { templates: number; entries: number } {
  const data = JSON.parse(json) as JournalStorage
  const storage = loadStorage()

  // Merge: новые шаблоны добавляем, существующие — пропускаем (по id)
  const existingTemplateIds = new Set(storage.templates.map((t) => t.id))
  let templatesAdded = 0
  for (const t of data.templates || []) {
    if (!existingTemplateIds.has(t.id)) {
      storage.templates.push(t)
      templatesAdded++
    }
  }

  const existingEntryIds = new Set(storage.entries.map((e) => e.id))
  let entriesAdded = 0
  for (const e of data.entries || []) {
    if (!existingEntryIds.has(e.id)) {
      storage.entries.push(e)
      entriesAdded++
    }
  }

  saveStorage(storage)
  return { templates: templatesAdded, entries: entriesAdded }
}

export function clearAllData() {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(STORAGE_KEY)
  }
}

// ─── Инициализация демо-данных (первый запуск) ──────────────────────────────

export function initDemoData(demoSchemas: JournalSchema[]) {
  const storage = loadStorage()
  if (storage.templates.length > 0) return // уже есть данные

  for (const schema of demoSchemas) {
    const template: JournalTemplate = {
      id: schema.id,
      title: schema.title,
      versions: [{ schema, entries: [] }],
      currentVersion: 1,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
    storage.templates.push(template)
  }

  saveStorage(storage)
}