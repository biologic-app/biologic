import { reactive } from 'vue'
import { useAuth } from '@/modules/auth'
import type { ApiClientError } from '@/shared/api/client.api'
import {
  createDoctor,
  createObject,
  fetchDirectionSamples,
  fetchRecentDirections,
  importDirections,
  loadDoctorOptions,
  normalizeSampleRow,
  loadObjectOptions,
  loadSampleTypeOptions,
  registerDirection,
  updateDirection,
  updateSample,
  type DirectionRow,
  type ImportType,
  type ReferenceOption,
  type SampleRow,
  type WorkflowImportSummary
} from '@/modules/directions/directions.api'

export type WizardStep = 0 | 1 | 2 | 3

export interface RegisterOutcome {
  ok: boolean
  code?: string
  message: string
}

const REGISTER_ERROR_MESSAGES: Record<string, string> = {
  direction_missing_samples: 'В направлении нет ни одного образца.',
  direction_missing_sample_data: 'У образцов не заполнены обязательные поля (название и тип образца).',
  direction_missing_research_assignments: 'Образцам не назначены исследования.',
  status_not_configured: 'Не настроен статус направления.'
}

const isApiClientError = (value: unknown): value is ApiClientError =>
  typeof value === 'object' && value !== null && 'status' in value && 'message' in value

const registerErrorMessage = (error: unknown): { code?: string; message: string } => {
  if (isApiClientError(error)) {
    const code = error.code
    return { code, message: (code && REGISTER_ERROR_MESSAGES[code]) || error.message }
  }
  return { message: 'Не удалось зарегистрировать направление.' }
}

export function useDirectionImport() {
  const auth = useAuth()

  const state = reactive({
    step: 0 as WizardStep,
    fileType: 'xlsx' as ImportType,
    fileName: '',
    importing: false,
    importError: '' as string,
    summary: null as WorkflowImportSummary | null,
    loadingResults: false,
    directions: [] as DirectionRow[],
    samplesByDirection: {} as Record<string, SampleRow[]>,
    currentIndex: 0,
    savingKey: '' as string,
    doctorOptions: [] as ReferenceOption[],
    objectOptions: [] as ReferenceOption[],
    sampleTypeOptions: [] as ReferenceOption[],
    registering: false,
    registerResults: {} as Record<string, RegisterOutcome>
  })

  let selectedFile: File | null = null

  const setFile = (file: File | null) => {
    selectedFile = file
    state.fileName = file?.name ?? ''
    state.importError = ''
  }

  const setFileType = (type: ImportType) => {
    state.fileType = type
  }

  const runImport = async (): Promise<boolean> => {
    if (!selectedFile || state.importing) {
      return false
    }
    state.importing = true
    state.importError = ''
    try {
      const response = await importDirections(selectedFile, state.fileType)
      state.summary = response.data
      state.step = 1
      await loadResults()
      return true
    } catch (error) {
      state.importError = isApiClientError(error) ? error.message : 'Проверьте файл и повторите импорт.'
      return false
    } finally {
      state.importing = false
    }
  }

  const loadResults = async () => {
    const created = state.summary?.directions_created ?? 0
    state.loadingResults = true
    try {
      const [doctors, objects, sampleTypes] = await Promise.all([
        loadDoctorOptions(),
        loadObjectOptions(),
        loadSampleTypeOptions()
      ])
      state.doctorOptions = doctors
      state.objectOptions = objects
      state.sampleTypeOptions = sampleTypes

      if (created <= 0) {
        state.directions = []
        state.samplesByDirection = {}
        return
      }

      const response = await fetchRecentDirections(Math.min(created, 200))
      // Импорт всегда создаёт направления в статусе draft; берём только их,
      // чтобы не зацепить более старые записи при точном совпадении лимита.
      const fresh = response.items
        .filter((row) => !row.status?.code || row.status.code === 'draft')
        .slice(0, created)
      state.directions = fresh

      const samplesEntries = await Promise.all(
        fresh.map(async (direction) => {
          const samples = await fetchDirectionSamples(direction.id)
          return [direction.id, samples.items.map(normalizeSampleRow)] as const
        })
      )
      state.samplesByDirection = Object.fromEntries(samplesEntries)
      state.currentIndex = 0
      state.registerResults = {}
    } finally {
      state.loadingResults = false
    }
  }

  const currentDirection = (): DirectionRow | null => state.directions[state.currentIndex] ?? null

  const goToStep = (step: WizardStep) => {
    state.step = step
  }

  const goToDirection = (index: number) => {
    if (index < 0 || index >= state.directions.length) {
      return
    }
    state.currentIndex = index
  }

  const nextDirection = () => goToDirection(state.currentIndex + 1)
  const prevDirection = () => goToDirection(state.currentIndex - 1)

  const patchDirection = (index: number, patch: Partial<DirectionRow>) => {
    const direction = state.directions[index]
    if (direction) {
      Object.assign(direction, patch)
    }
  }

  const saveDirection = async (id: string, body: Record<string, unknown>): Promise<boolean> => {
    state.savingKey = `direction:${id}`
    try {
      const response = await updateDirection(id, body)
      const index = state.directions.findIndex((row) => row.id === id)
      if (index >= 0) {
        Object.assign(state.directions[index], response.data)
      }
      return true
    } catch {
      return false
    } finally {
      state.savingKey = ''
    }
  }

  const saveSample = async (
    directionId: string,
    sampleId: string,
    body: Record<string, unknown>
  ): Promise<boolean> => {
    state.savingKey = `sample:${sampleId}`
    try {
      const response = await updateSample(sampleId, body)
      const samples = state.samplesByDirection[directionId] ?? []
      const index = samples.findIndex((row) => row.id === sampleId)
      if (index >= 0) {
        Object.assign(samples[index], normalizeSampleRow(response.data))
      }
      return true
    } catch {
      return false
    } finally {
      state.savingKey = ''
    }
  }

  const addDoctor = async (body: Record<string, unknown>): Promise<string | null> => {
    const response = await createDoctor(body)
    state.doctorOptions = await loadDoctorOptions()
    return response.data.id ?? null
  }

  const addObject = async (body: Record<string, unknown>): Promise<string | null> => {
    const response = await createObject(body)
    state.objectOptions = await loadObjectOptions()
    return response.data.id ?? null
  }

  const registerAll = async () => {
    const actorId = auth.user?.id ?? null
    state.registering = true
    try {
      for (const direction of state.directions) {
        if (state.registerResults[direction.id]?.ok) {
          continue
        }
        try {
          await registerDirection(direction.id, actorId, null)
          state.registerResults[direction.id] = { ok: true, message: 'Зарегистрировано.' }
        } catch (error) {
          const { code, message } = registerErrorMessage(error)
          state.registerResults[direction.id] = { ok: false, code, message }
        }
      }
    } finally {
      state.registering = false
    }
  }

  const reset = () => {
    selectedFile = null
    state.step = 0
    state.fileType = 'xlsx'
    state.fileName = ''
    state.importing = false
    state.importError = ''
    state.summary = null
    state.loadingResults = false
    state.directions = []
    state.samplesByDirection = {}
    state.currentIndex = 0
    state.savingKey = ''
    state.registering = false
    state.registerResults = {}
  }

  return Object.assign(state, {
    setFile,
    setFileType,
    runImport,
    loadResults,
    currentDirection,
    goToStep,
    goToDirection,
    nextDirection,
    prevDirection,
    patchDirection,
    saveDirection,
    saveSample,
    addDoctor,
    addObject,
    registerAll,
    reset
  })
}

export type DirectionImportContext = ReturnType<typeof useDirectionImport>
