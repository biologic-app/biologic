import {
  apiCommandRequest,
  apiCreateRequest,
  apiDeleteRequest,
  apiReadListRequest,
  apiReadRequest,
  apiUpdateRequest,
  loadReferenceOptions
} from '@/shared/api/client.api'

// Единый DTO ответа POST /directions/import (backend WorkflowImportSummary) —
// один и тот же для xlsx/.xls и json.
export interface ImportIssue {
  field?: string
  message?: string
  row?: number
  errors?: ImportIssue[]
  [key: string]: unknown
}

export interface WorkflowImportSummary {
  filename: string
  directions_created: number
  direction_ids: string[]
  samples_created: number
  research_created: number
  skipped: number
  errors: ImportIssue[]
  warnings: ImportIssue[]
}

export interface ReferenceLike {
  name?: string | null
  code?: string | null
  [key: string]: unknown
}

export interface DirectionRow {
  id: string
  year_no: number | null
  base_no: number | null
  doctor_id: string | null
  object_id: string | null
  status_id: string | null
  is_urgent: boolean | null
  is_done: boolean | null
  sampled_at: string | null
  received_at: string | null
  import_warnings: Record<string, unknown> | null
  doctor?: ReferenceLike | null
  object?: ReferenceLike | null
  status?: ReferenceLike | null
  [key: string]: unknown
}

export interface SampleRow {
  id: string
  // Текстовые поля нормализуются в пустую строку при загрузке (см. useDirectionImport),
  // чтобы их можно было напрямую биндить к UInput/UTextarea (они не принимают null).
  name: string
  alternate_name: string
  mass: string
  comment: string
  is_urgent: boolean | null
  sample_type_id: string | null
  direction_id: string | null
  status_id: string | null
  sample_type?: ReferenceLike | null
  status?: ReferenceLike | null
  [key: string]: unknown
}

// Приводит сырую строку образца из API к редактируемой форме (null → '').
export const normalizeSampleRow = (raw: SampleRow): SampleRow => ({
  ...raw,
  name: raw.name ?? '',
  alternate_name: raw.alternate_name ?? '',
  mass: raw.mass ?? '',
  comment: raw.comment ?? ''
})

export type ImportType = 'xlsx' | 'json' | 'xls'

export type ReferenceOption = { label: string; value: string | number | boolean | null }

// backend диспетчеризует .xls на legacy-парсер, но контракт принимает только
// `json` | `xlsx` в поле `type` (см. router.import_directions).
const toWireType = (type: ImportType): 'json' | 'xlsx' => (type === 'json' ? 'json' : 'xlsx')

export const importDirections = (file: File, type: ImportType) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('type', toWireType(type))
  return apiCommandRequest<WorkflowImportSummary>('/directions/import', {
    method: 'POST',
    body: formData
  })
}

export const fetchDirection = async (id: string): Promise<DirectionRow> => {
  const response = await apiReadRequest<DirectionRow>(`/directions/${id}`, {
    method: 'GET',
    params: { include: 'doctor,object,status' }
  })
  return response.data
}

export const fetchDirectionSamples = (directionId: string) =>
  apiReadListRequest<SampleRow>('/samples', {
    method: 'GET',
    params: {
      limit: 100,
      include: 'sample_type,status',
      filters: JSON.stringify({ direction_id: directionId })
    }
  })

export const updateDirection = (id: string, body: Record<string, unknown>) =>
  apiUpdateRequest<DirectionRow>(`/directions/${id}`, { method: 'PATCH', body })

export const updateSample = (id: string, body: Record<string, unknown>) =>
  apiUpdateRequest<SampleRow>(`/samples/${id}`, { method: 'PATCH', body })

export const registerDirection = (id: string, actorId: string | null, comment: string | null) =>
  apiCommandRequest<Record<string, unknown>>(`/directions/${id}/register`, {
    method: 'POST',
    body: { actor_id: actorId, comment }
  })

export const createDoctor = (body: Record<string, unknown>) =>
  apiCreateRequest<ReferenceLike & { id: string }>('/doctors', { method: 'POST', body })

export const createObject = (body: Record<string, unknown>) =>
  apiCreateRequest<ReferenceLike & { id: string }>('/objects', { method: 'POST', body })

export const loadDoctorOptions = () => loadReferenceOptions('/doctors')
export const loadObjectOptions = () => loadReferenceOptions('/objects')
export const loadSampleTypeOptions = () => loadReferenceOptions('/sample_types')

// Цель исследования, пригодная для отображения на образце (набор целей).
export interface ResearchGoalOption {
  id: string
  code: string | null
  name: string
  lab_id: string | null
  lab_name: string | null
}

// Строка существующего Research образца (read-эндпоинт GET /research).
export interface SampleResearchRow {
  id: string
  sample_id: string | null
  research_goal_id: string | null
  status_id: string | null
}

interface RawResearchGoal {
  id: string
  code?: string | null
  name?: string | null
  lab_id?: string | null
  lab_name?: string | null
}

// Лаборатория образца (проставлена импортом из меток легаси). Ключ к деривации целей.
export interface SampleLab {
  id: string
  code: string | null
  name: string | null
}

// Лаборатории образца: GET /samples/{id}/labs.
export const fetchSampleLabs = async (sampleId: string): Promise<SampleLab[]> => {
  const response = await apiReadListRequest<SampleLab>(`/samples/${sampleId}/labs`, {
    method: 'GET'
  })
  return response.items.map((row) => ({
    id: row.id,
    code: row.code ?? null,
    name: row.name ?? null
  }))
}

// Полная замена набора лабораторий образца: PUT /samples/{id}/labs.
export const updateSampleLabs = async (
  sampleId: string,
  labIds: string[]
): Promise<SampleLab[]> => {
  const response = await apiReadListRequest<SampleLab>(`/samples/${sampleId}/labs`, {
    method: 'PUT',
    body: { lab_ids: labIds }
  })
  return response.items.map((row) => ({
    id: row.id,
    code: row.code ?? null,
    name: row.name ?? null
  }))
}

export const loadLabOptions = () => loadReferenceOptions('/labs')

// Цели, выведенные из лабораторий образца, отфильтрованные по индикаторам выбранного
// типа: GET /samples/{id}/research-goal-suggestions?sample_type_id={typeId}.
// sample_type_id обязателен; пустой ответ — норма (нет меток/индикаторов).
export const fetchSampleResearchGoalSuggestions = async (
  sampleId: string,
  sampleTypeId: string
): Promise<ResearchGoalOption[]> => {
  const response = await apiReadListRequest<RawResearchGoal>(
    `/samples/${sampleId}/research-goal-suggestions`,
    { method: 'GET', params: { sample_type_id: sampleTypeId } }
  )
  return response.items.map((row) => ({
    id: row.id,
    code: row.code ?? null,
    name: row.name ?? '',
    lab_id: row.lab_id ?? null,
    lab_name: row.lab_name ?? null
  }))
}

// Полный справочник целей для ручного добавления. Лабораторию тянем из /labs
// (у research_goals есть только lab_id), чтобы показать имя лаборатории на цели.
export const fetchResearchGoalCatalog = async (): Promise<ResearchGoalOption[]> => {
  const [goals, labs] = await Promise.all([
    apiReadListRequest<RawResearchGoal>('/research_goals', {
      method: 'GET',
      params: { limit: 500, sort_by: 'name', sort_order: 'asc' }
    }),
    loadReferenceOptions('/labs')
  ])
  const labNameById = new Map(
    labs.map((option) => [String(option.value ?? ''), option.label] as const)
  )
  return goals.items.map((row) => ({
    id: row.id,
    code: row.code ?? null,
    name: row.name ?? '',
    lab_id: row.lab_id ?? null,
    lab_name: row.lab_id ? labNameById.get(String(row.lab_id)) ?? null : null
  }))
}

// Существующие Research образца — для инициализации набора целей и удаления.
export const fetchSampleResearch = async (
  sampleId: string
): Promise<SampleResearchRow[]> => {
  const response = await apiReadListRequest<SampleResearchRow>('/research', {
    method: 'GET',
    params: {
      limit: 200,
      filters: JSON.stringify({ sample_id: sampleId })
    }
  })
  return response.items
}

export const assignSampleResearch = (
  sampleId: string,
  researchGoalId: string,
  actorId: string | null
) =>
  apiCommandRequest<Record<string, unknown>>(`/samples/${sampleId}/assign-research`, {
    method: 'POST',
    body: { actor_id: actorId, research_goal_id: researchGoalId, comment: null }
  })

export const deleteResearch = (researchId: string) =>
  apiDeleteRequest<Record<string, unknown>>(`/research/${researchId}`, { method: 'DELETE' })