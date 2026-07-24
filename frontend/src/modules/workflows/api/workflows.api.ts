// api/workflows.api.ts
// Backend-backed replacement for the old localStorage `useJournalStorage`.
//
// Boundaries this adapter enforces (see US-003):
//  • The wire envelope is snake_case and is NOT camelCased on the way back
//    (project rule: only requests are converted). This adapter maps the
//    envelope ↔ the camelCase frontend models in `types/journal.ts`.
//  • `schema`, `answers`, `loops`, `history` are opaque JSONB: the authored
//    graph inside stays camelCase and must round-trip verbatim. Requests that
//    carry them are sent with `rawBody: true` so the shared client does not
//    recursively snake_case their nested keys.
//  • Schema versions are immutable on the backend (POST creates a new version
//    and bumps `current_version`). There is no draft endpoint, so
//    `updateCurrentSchema` only updates a client-side draft buffer; committing
//    a version goes through `saveSchemaVersion`.

import {
  apiCommandRequest,
  apiCreateRequest,
  apiDeleteRequest,
  apiReadListRequest,
  apiReadRequest,
  apiUpdateRequest,
  buildApiUrl,
} from '@/shared/api/client.api'
import type {
  DictionarySource,
  JournalActivityEvent,
  JournalActivityType,
  JournalAnswers,
  JournalComment,
  JournalEntry,
  JournalSchema,
  JournalStorage,
  JournalTemplate,
  JournalTemplateVersion,
} from '@/modules/workflows/types/journal'

// ─── Wire DTOs (snake_case, as serialized by the backend) ────────────────────

interface WireVersion {
  id: string
  template_id: string
  version: number
  schema: Record<string, unknown> // opaque JournalSchema-shaped graph
  created_at: string
}

interface WireTemplate {
  id: string
  title: string
  current_version: number
  created_at: string
  updated_at: string
  versions?: WireVersion[]
}

interface WireEvent {
  id: string
  run_id: string
  kind: string
  node_id: string | null
  payload: Record<string, unknown>
  author: string | null
  created_at: string
}

interface WireRun {
  id: string
  template_id: string
  schema_version: number
  scope_kind: string | null
  scope_id: string | null
  title: string
  status: string
  answers: Record<string, unknown>
  loops: Record<string, unknown>
  history: unknown[]
  current_node_id: string | null
  created_by: string | null
  created_at: string
  updated_at: string
  events?: WireEvent[]
}

export interface WireAttachment {
  id: string
  run_id: string
  field_id: string
  filename: string
  content_type: string | null
  size_bytes: number
  storage: string
  created_at: string
}

export interface ImportSummary {
  templates: number
  versions: number
  runs: number
  events: number
}

// Scope kind used when a run is attached to a research (the only scoped caller
// today — ResearchWorkflowTab passes the research id as `scope`).
const RESEARCH_SCOPE_KIND = 'research'

// ─── Mapping helpers ─────────────────────────────────────────────────────────

// A run reaching this node id is considered finished (mirrors the engine).
const END_NODE_ID = 'end'

const ENTRY_STATUSES = new Set(['draft', 'completed', 'archived'])

function toEntryStatus(status: string): JournalEntry['status'] {
  return ENTRY_STATUSES.has(status) ? (status as JournalEntry['status']) : 'draft'
}

// Backend event `kind` → frontend activity type. Comment events are surfaced as
// `comment_added` on the activity timeline (and additionally as a comment).
const KIND_TO_ACTIVITY: Record<string, JournalActivityType> = {
  comment: 'comment_added',
  created: 'created',
  step_completed: 'step_completed',
  comment_added: 'comment_added',
  reopened: 'reopened',
  completed: 'completed',
  reset: 'reset',
}

// The authenticated user's id (a UUID) for `created_by`. The old model stored a
// display name here, but the backend column is a user FK — a name would 422.
// Read straight from the persisted auth store to avoid composable lifecycle.
function resolveCreatedBy(): string | null {
  if (typeof window === 'undefined') {
    return null
  }
  try {
    const raw = localStorage.getItem('auth:user')
    if (!raw) {
      return null
    }
    const parsed = JSON.parse(raw) as { id?: string } | null
    return parsed?.id ?? null
  } catch {
    return null
  }
}

// Opaque schema graph + the version envelope → frontend JournalSchema. The
// stored graph is trusted verbatim; only id/version/updatedAt are re-derived
// from the envelope so the FE `version` matches the backend version number
// (JournalRunner filters runs by `schema.version`).
function toSchema(version: WireVersion): JournalSchema {
  const raw = (version.schema ?? {}) as Partial<JournalSchema>
  return {
    ...(raw as JournalSchema),
    id: version.template_id,
    version: version.version,
    updatedAt: version.created_at,
  }
}

function toEntry(run: WireRun): JournalEntry {
  const comments: JournalComment[] = []
  const activity: JournalActivityEvent[] = []

  for (const event of run.events ?? []) {
    const author = event.author || 'Аноним'
    const label = typeof event.payload?.label === 'string' ? event.payload.label : undefined
    if (event.kind === 'comment') {
      comments.push({
        id: event.id,
        nodeId: event.node_id ?? '',
        author,
        text: typeof event.payload?.text === 'string' ? event.payload.text : '',
        createdAt: event.created_at,
      })
    }
    const type = KIND_TO_ACTIVITY[event.kind]
    if (type) {
      activity.push({
        id: event.id,
        type,
        author,
        at: event.created_at,
        ...(event.node_id ? { nodeId: event.node_id } : {}),
        ...(label ? { label } : {}),
      })
    }
  }

  return {
    id: run.id,
    schemaId: run.template_id,
    schemaVersion: run.schema_version,
    ...(run.scope_id ? { scope: run.scope_id } : {}),
    title: run.title,
    status: toEntryStatus(run.status),
    answers: (run.answers ?? {}) as JournalAnswers,
    loops: (run.loops ?? {}) as Record<string, JournalAnswers[]>,
    history: (run.history ?? []) as string[],
    currentNodeId: run.current_node_id ?? 'start',
    ...(run.created_by ? { createdBy: run.created_by, updatedBy: run.created_by } : {}),
    comments,
    activity,
    startedAt: run.created_at,
    updatedAt: run.updated_at,
    ...(run.status === 'completed' ? { completedAt: run.updated_at } : {}),
  }
}

function toTemplateRow(row: WireTemplate): JournalTemplate {
  return {
    id: row.id,
    title: row.title,
    versions: [],
    currentVersion: row.current_version,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  }
}

// Inject the v2 format marker the backend validator requires. Everything else
// in the authored graph is preserved so the round-trip is lossless.
function toWireSchema(schema: JournalSchema): Record<string, unknown> {
  return { ...schema, formatVersion: 2 }
}

// ─── Client-side draft buffer (no backend draft endpoint) ────────────────────

const draftSchemas = new Map<string, JournalSchema>()

function clearDraft(templateId: string) {
  draftSchemas.delete(templateId)
}

// ─── Templates ────────────────────────────────────────────────────────────────

export async function listTemplates(): Promise<JournalTemplate[]> {
  const response = await apiReadListRequest<WireTemplate>('/workflow-templates', {
    method: 'GET',
    params: { limit: 100, sort_by: 'updated_at', sort_order: 'desc' },
  })
  return response.items.map(toTemplateRow)
}

export async function getTemplate(id: string): Promise<JournalTemplate | undefined> {
  const response = await apiReadRequest<WireTemplate>(`/workflow-templates/${id}`, {
    method: 'GET',
    params: { include: 'versions' },
  })
  const template = response.data
  const runs = await getEntriesForSchema(id)
  const runsByVersion = new Map<number, JournalEntry[]>()
  for (const run of runs) {
    const bucket = runsByVersion.get(run.schemaVersion) ?? []
    bucket.push(run)
    runsByVersion.set(run.schemaVersion, bucket)
  }
  const versions: JournalTemplateVersion[] = (template.versions ?? [])
    .slice()
    .sort((a, b) => a.version - b.version)
    .map((version) => ({
      schema: toSchema(version),
      entries: runsByVersion.get(version.version) ?? [],
    }))
  return {
    id: template.id,
    title: template.title,
    versions,
    currentVersion: template.current_version,
    createdAt: template.created_at,
    updatedAt: template.updated_at,
  }
}

export async function createTemplate(
  title: string,
  initialSchema: JournalSchema,
): Promise<JournalTemplate> {
  const created = await apiCreateRequest<WireTemplate>('/workflow-templates', {
    method: 'POST',
    body: { title },
  })
  const templateId = created.data.id
  await saveSchemaVersion(templateId, initialSchema)
  const template = await getTemplate(templateId)
  if (!template) {
    throw new Error(`Template "${templateId}" not found right after creation`)
  }
  return template
}

export async function renameTemplate(templateId: string, newTitle: string): Promise<void> {
  await apiUpdateRequest<WireTemplate>(`/workflow-templates/${templateId}`, {
    method: 'PATCH',
    body: { title: newTitle },
  })
}

export async function deleteTemplate(templateId: string): Promise<void> {
  await apiDeleteRequest<Record<string, unknown>>(`/workflow-templates/${templateId}`, {
    method: 'DELETE',
  })
}

export async function saveSchemaVersion(
  templateId: string,
  schema: JournalSchema,
): Promise<JournalTemplate> {
  await apiCreateRequest<WireVersion>(`/workflow-templates/${templateId}/versions`, {
    method: 'POST',
    body: toWireSchema(schema),
    rawBody: true,
  })
  clearDraft(templateId)
  const template = await getTemplate(templateId)
  if (!template) {
    throw new Error(`Template "${templateId}" not found after saving a version`)
  }
  return template
}

// No backend draft endpoint: versions are immutable, so the builder's autosave
// only parks the working schema in a client-side buffer. `saveSchemaVersion`
// (explicit "new version") is what actually persists.
export async function updateCurrentSchema(
  templateId: string,
  schema: JournalSchema,
): Promise<void> {
  draftSchemas.set(templateId, schema)
}

export async function getSchema(
  templateId: string,
  version?: number,
): Promise<JournalSchema | undefined> {
  if (version === undefined && draftSchemas.has(templateId)) {
    return draftSchemas.get(templateId)
  }
  const template = await getTemplate(templateId)
  if (!template) {
    return undefined
  }
  const target = version ?? template.currentVersion
  return template.versions[target - 1]?.schema
}

export async function getSchemaVersions(templateId: string): Promise<JournalSchema[]> {
  const template = await getTemplate(templateId)
  return template ? template.versions.map((version) => version.schema) : []
}

export async function exportTemplate(templateId: string): Promise<string> {
  const template = await getTemplate(templateId)
  if (!template) {
    throw new Error('Template not found')
  }
  return JSON.stringify(template, null, 2)
}

// ─── Runs (entries) ────────────────────────────────────────────────────────────

export async function listRuns(): Promise<JournalEntry[]> {
  const response = await apiReadListRequest<WireRun>('/workflow-runs', {
    method: 'GET',
    params: { limit: 200, sort_by: 'updated_at', sort_order: 'desc' },
  })
  return response.items.map(toEntry)
}

// Run counts keyed by template id — cheap fill for the templates table without
// an N+1 fan-out (the per-version entry lists come from `getTemplate`).
export async function countRunsByTemplate(): Promise<Record<string, number>> {
  const runs = await listRuns()
  const counts: Record<string, number> = {}
  for (const run of runs) {
    counts[run.schemaId] = (counts[run.schemaId] ?? 0) + 1
  }
  return counts
}

export async function getEntriesForSchema(
  templateId: string,
  version?: number,
  scope?: string,
): Promise<JournalEntry[]> {
  const filters: Record<string, unknown> = { template_id: templateId }
  if (version !== undefined) {
    filters.schema_version = version
  }
  if (scope !== undefined) {
    filters.scope_id = scope
  }
  const response = await apiReadListRequest<WireRun>('/workflow-runs', {
    method: 'GET',
    params: { limit: 200, filters: JSON.stringify(filters) },
  })
  return response.items.map(toEntry)
}

export async function getEntry(entryId: string): Promise<JournalEntry | undefined> {
  const response = await apiReadRequest<WireRun>(`/workflow-runs/${entryId}`, {
    method: 'GET',
    params: { include: 'events' },
  })
  return toEntry(response.data)
}

export async function createEntry(
  templateId: string,
  version: number,
  title: string,
  scope?: string,
): Promise<JournalEntry> {
  const body = {
    template_id: templateId,
    schema_version: version,
    title,
    scope_kind: scope !== undefined ? RESEARCH_SCOPE_KIND : null,
    scope_id: scope ?? null,
    current_node_id: 'start',
    created_by: resolveCreatedBy(),
  }
  const response = await apiCreateRequest<WireRun>('/workflow-runs', {
    method: 'POST',
    body,
    rawBody: true,
  })
  return toEntry(response.data)
}

export async function saveEntryProgress(
  entryId: string,
  answers: JournalAnswers,
  history: string[],
  currentNodeId: string,
  loops?: Record<string, JournalAnswers[]>,
): Promise<JournalEntry> {
  const body: Record<string, unknown> = {
    answers,
    history,
    current_node_id: currentNodeId,
  }
  if (loops) {
    body.loops = loops
  }
  const updated = await apiUpdateRequest<WireRun>(`/workflow-runs/${entryId}`, {
    method: 'PATCH',
    body,
    rawBody: true,
  })
  let run = updated.data
  // Status changes only through commands: reaching the end node completes the
  // run (PATCH cannot set status).
  if (currentNodeId === END_NODE_ID && run.status !== 'completed') {
    const completed = await apiCommandRequest<WireRun>(`/workflow-runs/${entryId}/complete`, {
      method: 'POST',
    })
    run = completed.data
  }
  return toEntry(run)
}

export async function addComment(
  entryId: string,
  nodeId: string,
  author: string,
  text: string,
): Promise<void> {
  await apiCreateRequest<WireEvent>(`/workflow-runs/${entryId}/comments`, {
    method: 'POST',
    body: { text, node_id: nodeId, author },
  })
}

// NOTE: there is no generic activity-event endpoint (only comments and the
// structured execute-step flow), so step/lifecycle activity is not persisted at
// this stage — the timeline is driven by persisted comment events instead.
// A `logActivity` shim was intentionally dropped rather than kept as dead code.

export async function completeRun(entryId: string): Promise<JournalEntry> {
  const response = await apiCommandRequest<WireRun>(`/workflow-runs/${entryId}/complete`, {
    method: 'POST',
  })
  return toEntry(response.data)
}

// ─── Execute-step (domain actions, US-007) ────────────────────────────────────

// One action on the wire: the backend reads `command` + opaque `resolved_args`
// (target id under the command's targetKey, plus command args like actor_id).
export interface ExecuteStepActionPayload {
  actionId: string
  command: string
  resolvedArgs: Record<string, unknown>
}

export interface ExecuteStepPayload {
  nodeId: string
  attempt: number
  actions: ExecuteStepActionPayload[]
  // Top-level fallback actor for actions whose resolved_args omit `actor_id`.
  actorId?: string | null
  author?: string | null
}

export interface ExecuteStepOutcome {
  status: 'applied' | 'already_applied'
  alreadyApplied: boolean
  results: unknown[]
}

// Run a step's domain actions server-side (schema-doc §6). The whole body is sent
// with `rawBody: true` so `resolved_args` round-trips verbatim: its keys are the
// command's argument names (already snake_case) and its values must not be
// mangled by the request key converter. A forbidden transition surfaces as a 409
// `ApiClientError` (DomainConflictError) — the caller is expected to show it, not
// swallow it. The response envelope is snake_case and is NOT camelCased on read.
export async function executeStep(
  runId: string,
  payload: ExecuteStepPayload,
): Promise<ExecuteStepOutcome> {
  const body = {
    node_id: payload.nodeId,
    attempt: payload.attempt,
    actions: payload.actions.map((action) => ({
      action_id: action.actionId,
      command: action.command,
      resolved_args: action.resolvedArgs,
    })),
    ...(payload.actorId ? { actor_id: payload.actorId } : {}),
    ...(payload.author ? { author: payload.author } : {}),
  }
  const response = await apiCommandRequest<Record<string, unknown>>(
    `/workflow-runs/${runId}/execute-step`,
    { method: 'POST', body, rawBody: true },
  )
  const data = response.data
  const alreadyApplied = data.already_applied === true
  return {
    status: alreadyApplied ? 'already_applied' : 'applied',
    alreadyApplied,
    results: Array.isArray(data.results) ? data.results : [],
  }
}

export async function archiveRun(entryId: string): Promise<JournalEntry> {
  const response = await apiCommandRequest<WireRun>(`/workflow-runs/${entryId}/archive`, {
    method: 'POST',
  })
  return toEntry(response.data)
}

export async function deleteEntry(entryId: string): Promise<void> {
  await apiDeleteRequest<Record<string, unknown>>(`/workflow-runs/${entryId}`, {
    method: 'DELETE',
  })
}

// ─── Attachments ────────────────────────────────────────────────────────────

export async function uploadAttachment(
  runId: string,
  fieldId: string,
  file: File,
): Promise<WireAttachment> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('field_id', fieldId)
  const response = await apiCreateRequest<WireAttachment>(
    `/workflow-runs/${runId}/attachments`,
    { method: 'POST', body: formData },
  )
  return response.data
}

export function getAttachmentUrl(attachmentId: string): string {
  return buildApiUrl(`/workflow-attachments/${attachmentId}`)
}

// ─── Dictionary field options (type: 'dictionary') ───────────────────────────

export interface DictionaryOption {
  label: string
  value: string | number | boolean | null
}

// Wire rows are snake_case and are NOT camelCased on read (project rule), so
// labelKey/valueKey (e.g. 'full_name') index the raw row verbatim.
const MAX_DICTIONARY_OPTIONS = 500

// Cache per (endpoint, keys, filters): dictionary options rarely change during a
// run and every dictionary field/table cell would otherwise refetch on mount.
const dictionaryOptionsCache = new Map<string, Promise<DictionaryOption[]>>()

function dictionaryCacheKey(source: DictionarySource, valueKey: string, labelKey: string): string {
  return JSON.stringify([source.endpoint, valueKey, labelKey, source.filters ?? null])
}

async function fetchDictionaryOptions(
  source: DictionarySource,
  valueKey: string,
  labelKey: string,
): Promise<DictionaryOption[]> {
  const endpoint = source.endpoint.startsWith('/') ? source.endpoint : `/${source.endpoint}`
  const params: Record<string, unknown> = { limit: MAX_DICTIONARY_OPTIONS }
  if (source.filters && Object.keys(source.filters).length) {
    params.filters = JSON.stringify(source.filters)
  }
  const response = await apiReadListRequest<Record<string, unknown>>(endpoint, {
    method: 'GET',
    params,
  })
  return response.items.map((row) => {
    const rawValue = row[valueKey] ?? row.id ?? null
    const value =
      typeof rawValue === 'string'
      || typeof rawValue === 'number'
      || typeof rawValue === 'boolean'
        ? rawValue
        : rawValue == null
          ? null
          : String(rawValue)
    const rawLabel = row[labelKey] ?? row.name ?? row.id
    return { label: rawLabel == null ? String(value) : String(rawLabel), value }
  })
}

// Load (and cache) the options for a dictionary field. Honours valueKey/labelKey
// (defaults 'id'/'name') and static filters; `searchable` is a render concern
// (client-side filter in USelectMenu), not a fetch concern.
export function loadDictionaryOptions(source: DictionarySource): Promise<DictionaryOption[]> {
  const valueKey = source.valueKey ?? 'id'
  const labelKey = source.labelKey ?? 'name'
  const key = dictionaryCacheKey(source, valueKey, labelKey)
  const cached = dictionaryOptionsCache.get(key)
  if (cached) {
    return cached
  }
  const promise = fetchDictionaryOptions(source, valueKey, labelKey).catch((error) => {
    // Do not cache failures — allow a later retry to refetch.
    dictionaryOptionsCache.delete(key)
    throw error
  })
  dictionaryOptionsCache.set(key, promise)
  return promise
}

// ─── Import (old localStorage bundle → backend) ──────────────────────────────

interface ImportEventBody {
  kind: string
  node_id: string | null
  payload: Record<string, unknown>
  author: string | null
}

interface ImportRunBody {
  schema_version: number
  title: string
  status: string
  scope_kind: string | null
  scope_id: string | null
  answers: JournalAnswers
  loops: Record<string, JournalAnswers[]>
  history: string[]
  current_node_id: string | null
  created_by: string | null
  events: ImportEventBody[]
}

function toImportRun(entry: JournalEntry): ImportRunBody {
  const events: ImportEventBody[] = [
    ...(entry.comments ?? []).map((comment) => ({
      kind: 'comment',
      node_id: comment.nodeId || null,
      payload: { text: comment.text } as Record<string, unknown>,
      author: comment.author || null,
    })),
    // Comment activity is already carried by the comment events above.
    ...(entry.activity ?? [])
      .filter((event) => event.type !== 'comment_added')
      .map((event) => ({
        kind: event.type,
        node_id: event.nodeId || null,
        payload: (event.label ? { label: event.label } : {}) as Record<string, unknown>,
        author: event.author || null,
      })),
  ]
  return {
    schema_version: entry.schemaVersion,
    title: entry.title,
    status: entry.status,
    scope_kind: entry.scope ? RESEARCH_SCOPE_KIND : null,
    scope_id: entry.scope ?? null,
    answers: entry.answers ?? {},
    loops: entry.loops ?? {},
    history: entry.history ?? [],
    current_node_id: entry.currentNodeId ?? null,
    // Old data stored a display name here — not importable as a user FK.
    created_by: null,
    events,
  }
}

// Accepts either a full storage bundle ({templates, entries}) or a single
// exported template ({id, title, versions, ...}); runs are gathered from both
// the top-level `entries` and each template's `versions[].entries`.
export async function importData(json: string): Promise<ImportSummary> {
  const parsed = JSON.parse(json) as Partial<JournalStorage> & Partial<JournalTemplate>
  const storage: JournalStorage = Array.isArray(parsed.templates)
    ? (parsed as JournalStorage)
    : {
        templates: parsed.id ? [parsed as JournalTemplate] : [],
        entries: [],
      }

  const templates = storage.templates.map((template) => {
    const seen = new Set<string>()
    const runs: ImportRunBody[] = []
    const collect = (entry: JournalEntry) => {
      if (seen.has(entry.id)) {
        return
      }
      seen.add(entry.id)
      runs.push(toImportRun(entry))
    }
    for (const entry of storage.entries ?? []) {
      if (entry.schemaId === template.id) {
        collect(entry)
      }
    }
    for (const version of template.versions ?? []) {
      for (const entry of version.entries ?? []) {
        collect(entry)
      }
    }
    return {
      title: template.title,
      current_version: template.currentVersion,
      versions: (template.versions ?? []).map((version, index) => ({
        version: index + 1,
        schema: toWireSchema(version.schema),
      })),
      runs,
    }
  })

  const response = await apiCommandRequest<ImportSummary>('/workflow-templates/import', {
    method: 'POST',
    body: { templates },
    rawBody: true,
  })
  return response.data
}

// ─── Demo seeding (first run) ────────────────────────────────────────────────

// Idempotent by emptiness: seed the demo templates only when there are none.
export async function initDemoData(demoSchemas: JournalSchema[]): Promise<void> {
  const existing = await listTemplates()
  if (existing.length) {
    return
  }
  for (const schema of demoSchemas) {
    await createTemplate(schema.title, schema)
  }
}
