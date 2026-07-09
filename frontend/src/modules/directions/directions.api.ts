import {
  apiCommandRequest,
  apiCreateRequest,
  apiReadListRequest,
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

export const fetchRecentDirections = (limit: number) =>
  apiReadListRequest<DirectionRow>('/directions', {
    method: 'GET',
    params: {
      limit,
      sort_by: 'created_at',
      sort_order: 'desc',
      include: 'doctor,object,status'
    }
  })

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
