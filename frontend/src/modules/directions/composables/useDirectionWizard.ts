import { reactive } from 'vue'
import { useAuth } from '@/modules/auth'
import { i18n } from '@/shared/i18n'
import type { ApiClientError } from '@/shared/api/client.api'

const t = (key: string, params?: Record<string, unknown>) =>
  i18n.global.t(key, params ?? {}).toString()
import {
  assignSampleResearch,
  createDirection,
  createDoctor,
  createObject,
  createSample,
  deleteResearch,
  deleteSample,
  fetchDirection,
  fetchDirectionSamples,
  fetchNextBaseNo,
  fetchResearchGoalCatalog,
  fetchSampleLabs,
  fetchSampleResearch,
  fetchSampleResearchGoalSuggestions,
  importDirections,
  loadDoctorOptions,
  loadLabOptions,
  updateSampleLabs,
  normalizeSampleRow,
  loadObjectOptions,
  loadSampleTypeOptions,
  registerDirection,
  updateDirection,
  updateSample,
  type DirectionRow,
  type ImportType,
  type ReferenceOption,
  type ResearchGoalOption,
  type SampleLab,
  type SampleRow,
  type WorkflowImportSummary
} from '@/modules/directions/directions.api'

// Шаги мастера. Активный набор зависит от режима (см. WizardMode):
//   import: upload → review → fill → register
//   manual/draft: fill → register (реквизиты встроены в шаг fill)
export type WizardStep = 'select' | 'upload' | 'review' | 'fill' | 'register'

// Режим наполнения: экран выбора, импорт из файла, ручное создание,
// либо дозаполнение уже существующего черновика (открыт из строки таблицы).
export type WizardMode = 'select' | 'import' | 'manual' | 'draft'

export interface RegisterOutcome {
  ok: boolean
  code?: string
  message: string
}

// Значения — i18n-ключи (не готовый текст), резолвятся в registerErrorMessage
// через t() в момент показа, чтобы переключение языка применялось сразу.
const REGISTER_ERROR_MESSAGE_KEYS: Record<string, string> = {
  direction_missing_samples: 'directionWizard.errorMissingSamples',
  direction_missing_sample_data: 'directionWizard.errorMissingSampleData',
  direction_missing_research_assignments: 'directionWizard.errorMissingResearchAssignments',
  direction_missing_doctor_or_object: 'directionWizard.errorMissingDoctorOrObject',
  status_not_configured: 'directionWizard.errorStatusNotConfigured'
}

const isApiClientError = (value: unknown): value is ApiClientError =>
  typeof value === 'object' && value !== null && 'status' in value && 'message' in value

const registerErrorMessage = (error: unknown): { code?: string; message: string } => {
  if (isApiClientError(error)) {
    const code = error.code
    const messageKey = code && REGISTER_ERROR_MESSAGE_KEYS[code]
    return { code, message: (messageKey && t(messageKey)) || error.message }
  }
  return { message: t('directionWizard.errorFailedToRegisterDirection') }
}

export function useDirectionWizard() {
  const auth = useAuth()

  const state = reactive({
    step: 'select' as WizardStep,
    // Режим мастера. 'draft' — открыт из строки таблицы сразу на шаге
    // дозаполнения; 'manual' — ручное создание (черновик создан заранее);
    // 'import' — импорт из файла; 'select' — экран выбора режима.
    mode: 'select' as WizardMode,
    fileType: 'xlsx' as ImportType,
    fileName: '',
    fileSize: 0,
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
    // Справочник лабораторий (для редактирования набора лабораторий образца).
    labOptions: [] as ReferenceOption[],
    // Полный справочник целей исследования (для ручного добавления на образец).
    researchGoalCatalog: [] as ResearchGoalOption[],
    // Набор выбранных research_goal_id на образец (per-sample).
    researchGoalsBySample: {} as Record<string, string[]>,
    // Карта `${sampleId}:${researchGoalId}` → research_id (существующие Research, для удаления).
    researchIdByKey: {} as Record<string, string>,
    // Метаданные цели (имя + лаборатория) для отображения и каскадного удаления
    // целей при снятии лаборатории с образца.
    goalLabById: {} as Record<string, { name: string; lab_id: string | null; lab_name: string | null }>,
    // Лаборатории образца (проставлены импортом из меток) — источник деривации целей.
    labsBySample: {} as Record<string, SampleLab[]>,
    // Направления, для которых уже подгружены существующие Research (ленивая инициализация).
    researchLoadedDirections: {} as Record<string, boolean>,
    registering: false,
    registerResults: {} as Record<string, RegisterOutcome>
  })

  // Кеш выведенных целей по ключу `${sampleId}:${sampleTypeId}` (деривация зависит
  // и от типа, и от лабораторий конкретного образца). Не реактивный — вспомогательный.
  const suggestionsCache = new Map<string, ResearchGoalOption[]>()

  let selectedFile: File | null = null

  const setFile = (file: File | null) => {
    selectedFile = file
    state.fileName = file?.name ?? ''
    state.fileSize = file?.size ?? 0
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
      state.step = 'review'
      await loadResults()
      return true
    } catch (error) {
      state.importError = isApiClientError(error) ? error.message : t('directionWizard.errorCheckFileAndRetry')
      return false
    } finally {
      state.importing = false
    }
  }

  // Общая загрузка справочников для шага дозаполнения (врачи, объекты, типы
  // образцов, лаборатории, полный каталог целей). Используется всеми режимами.
  const loadFillOptions = async () => {
    const [doctors, objects, sampleTypes, labs, goalCatalog] = await Promise.all([
      loadDoctorOptions(),
      loadObjectOptions(),
      loadSampleTypeOptions(),
      loadLabOptions().catch(() => [] as ReferenceOption[]),
      fetchResearchGoalCatalog().catch(() => [] as ResearchGoalOption[])
    ])
    state.doctorOptions = doctors
    state.objectOptions = objects
    state.sampleTypeOptions = sampleTypes
    state.labOptions = labs
    state.researchGoalCatalog = goalCatalog
    for (const goal of goalCatalog) {
      state.goalLabById[goal.id] = { name: goal.name, lab_id: goal.lab_id, lab_name: goal.lab_name }
    }
  }

  const loadResults = async () => {
    const directionIds = state.summary?.direction_ids ?? []
    state.loadingResults = true
    try {
      await loadFillOptions()

      if (!directionIds.length) {
        state.directions = []
        state.samplesByDirection = {}
        return
      }

      // Направления загружаются строго по id из ответа импорта, а не эвристикой
      // «последние N со статусом draft» — та ломалась, если между импортом и
      // загрузкой результатов где-то создавалось/менялось другое направление.
      const fresh = await Promise.all(directionIds.map((id) => fetchDirection(id)))
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
      state.researchGoalsBySample = {}
      state.researchIdByKey = {}
      state.labsBySample = {}
      state.researchLoadedDirections = {}
    } finally {
      state.loadingResults = false
    }
  }

  // Наполнить шаг дозаполнения одним направлением: справочники, само направление,
  // его образцы и существующие Research (набор целей). Общий код для manual/draft.
  const hydrateFillStep = async (directionId: string) => {
    state.loadingResults = true
    state.step = 'fill'
    try {
      await loadFillOptions()
      const direction = await fetchDirection(directionId)
      state.directions = [direction]
      const samples = await fetchDirectionSamples(direction.id)
      state.samplesByDirection = { [direction.id]: samples.items.map(normalizeSampleRow) }
      state.currentIndex = 0
      await ensureResearchForDirection(direction.id)
    } finally {
      state.loadingResults = false
    }
  }

  // Открыть мастер для уже существующего draft-направления (из строки таблицы).
  const loadExistingDraft = async (directionId: string) => {
    reset()
    state.mode = 'draft'
    await hydrateFillStep(directionId)
  }

  // Экран выбора → импорт из файла.
  const chooseImport = () => {
    state.mode = 'import'
    state.step = 'upload'
  }

  // Экран выбора → ручное создание: сразу создаём пустой черновик с авто-нумерацией
  // (год = текущий, base_no = следующий за год; оба редактируемы в шаге дозаполнения)
  // и переходим на шаг дозаполнения. При конфликте номера backend вернёт ошибку.
  const startManual = async (): Promise<{ ok: boolean; message?: string }> => {
    reset()
    state.mode = 'manual'
    state.loadingResults = true
    try {
      const yearNo = new Date().getFullYear()
      const baseNo = await fetchNextBaseNo(yearNo).catch(() => null)
      const created = await createDirection({ year_no: yearNo, base_no: baseNo })
      await hydrateFillStep(created.data.id)
      return { ok: true }
    } catch (error) {
      state.mode = 'select'
      state.step = 'select'
      state.loadingResults = false
      return {
        ok: false,
        message: isApiClientError(error) ? error.message : t('directionWizard.failedToCreateDirectionMessage')
      }
    }
  }

  // Добавить пустой образец в направление (POST) и положить его в состояние.
  // Возвращает id нового образца (для авто-раскрытия в аккордеоне) либо null.
  const addSample = async (directionId: string): Promise<string | null> => {
    try {
      const response = await createSample(directionId, { name: '' })
      const row = normalizeSampleRow(response.data)
      const list = state.samplesByDirection[directionId] ?? []
      state.samplesByDirection[directionId] = [...list, row]
      return row.id
    } catch {
      return null
    }
  }

  // Удалить образец (DELETE) и вычистить связанные с ним карты состояния.
  const removeSample = async (directionId: string, sampleId: string): Promise<boolean> => {
    try {
      await deleteSample(sampleId)
      const list = state.samplesByDirection[directionId] ?? []
      state.samplesByDirection[directionId] = list.filter((sample) => sample.id !== sampleId)
      delete state.researchGoalsBySample[sampleId]
      delete state.labsBySample[sampleId]
      const prefix = `${sampleId}:`
      for (const key of Object.keys(state.researchIdByKey)) {
        if (key.startsWith(prefix)) {
          delete state.researchIdByKey[key]
        }
      }
      for (const key of suggestionsCache.keys()) {
        if (key.startsWith(prefix)) {
          suggestionsCache.delete(key)
        }
      }
      return true
    } catch {
      return false
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

  const researchGoalCatalogById = () =>
    new Map(state.researchGoalCatalog.map((goal) => [goal.id, goal] as const))

  // Перечитывает существующие Research образца с сервера и синхронизирует карты.
  const loadSampleResearch = async (sampleId: string) => {
    const rows = await fetchSampleResearch(sampleId)
    const prefix = `${sampleId}:`
    for (const key of Object.keys(state.researchIdByKey)) {
      if (key.startsWith(prefix)) {
        delete state.researchIdByKey[key]
      }
    }
    const catalog = researchGoalCatalogById()
    const goalIds: string[] = []
    for (const row of rows) {
      if (!row.research_goal_id) {
        continue
      }
      goalIds.push(row.research_goal_id)
      state.researchIdByKey[`${prefix}${row.research_goal_id}`] = row.id
      const meta = catalog.get(row.research_goal_id)
      if (meta && !state.goalLabById[row.research_goal_id]) {
        state.goalLabById[row.research_goal_id] = {
          name: meta.name,
          lab_id: meta.lab_id,
          lab_name: meta.lab_name
        }
      }
    }
    state.researchGoalsBySample[sampleId] = goalIds
  }

  const findSample = (sampleId: string): SampleRow | null => {
    for (const samples of Object.values(state.samplesByDirection)) {
      const found = samples.find((sample) => sample.id === sampleId)
      if (found) {
        return found
      }
    }
    return null
  }

  // Полная замена набора лабораторий образца. Цели снятых лабораторий каскадно
  // убираются; деривация (тип образца + лаборатория) подтягивает цели ТОЛЬКО
  // добавленных лабораторий — ручные удаления целей остальных лабораторий не
  // затираются. Кеш деривации инвалидируется.
  const setSampleLabs = async (sampleId: string, labIds: string[]): Promise<boolean> => {
    try {
      const previous = new Set((state.labsBySample[sampleId] ?? []).map((lab) => lab.id))
      const labs = await updateSampleLabs(sampleId, labIds)
      state.labsBySample[sampleId] = labs
      const allowed = new Set(labs.map((lab) => lab.id))
      const current = state.researchGoalsBySample[sampleId] ?? []
      const kept = current.filter((goalId) => {
        const labId = state.goalLabById[goalId]?.lab_id
        return !labId || allowed.has(labId)
      })
      state.researchGoalsBySample[sampleId] = kept
      const prefix = `${sampleId}:`
      for (const key of suggestionsCache.keys()) {
        if (key.startsWith(prefix)) {
          suggestionsCache.delete(key)
        }
      }
      const addedLabIds = new Set(labs.map((lab) => lab.id).filter((id) => !previous.has(id)))
      const sampleTypeId = findSample(sampleId)?.sample_type_id ?? null
      if (addedLabIds.size && sampleTypeId) {
        const suggestions = await fetchSampleResearchGoalSuggestions(sampleId, sampleTypeId)
        suggestionsCache.set(`${sampleId}:${sampleTypeId}`, suggestions)
        const merged = [...(state.researchGoalsBySample[sampleId] ?? [])]
        for (const goal of suggestions) {
          state.goalLabById[goal.id] = { name: goal.name, lab_id: goal.lab_id, lab_name: goal.lab_name }
          if (goal.lab_id && addedLabIds.has(goal.lab_id) && !merged.includes(goal.id)) {
            merged.push(goal.id)
          }
        }
        state.researchGoalsBySample[sampleId] = merged
      }
      return true
    } catch {
      return false
    }
  }

  // Подгружает лаборатории образца (проставлены импортом из меток легаси).
  const loadSampleLabs = async (sampleId: string) => {
    state.labsBySample[sampleId] = await fetchSampleLabs(sampleId)
  }

  // Ленивая инициализация по образцам направления: существующие Research (набор целей)
  // и лаборатории образца (источник деривации целей).
  const ensureResearchForDirection = async (directionId: string) => {
    if (state.researchLoadedDirections[directionId]) {
      return
    }
    const samples = state.samplesByDirection[directionId] ?? []
    try {
      await Promise.all(
        samples.flatMap((sample) => [loadSampleResearch(sample.id), loadSampleLabs(sample.id)])
      )
      state.researchLoadedDirections[directionId] = true
    } catch {
      // Оставляем неотмеченным, чтобы повторить при следующем входе на направление.
    }
  }

  // Авто-подстановка целей, выведенных сервером из (тип образца + лаборатории образца).
  // Union без затирания вручную выбранных/уже назначенных; пустой ответ — норма.
  const applySampleTypeDefaults = async (sampleId: string, sampleTypeId: string | null) => {
    if (!sampleTypeId) {
      return
    }
    const cacheKey = `${sampleId}:${sampleTypeId}`
    let suggestions = suggestionsCache.get(cacheKey)
    if (!suggestions) {
      suggestions = await fetchSampleResearchGoalSuggestions(sampleId, sampleTypeId)
      suggestionsCache.set(cacheKey, suggestions)
    }
    const merged = [...(state.researchGoalsBySample[sampleId] ?? [])]
    for (const goal of suggestions) {
      state.goalLabById[goal.id] = { name: goal.name, lab_id: goal.lab_id, lab_name: goal.lab_name }
      if (!merged.includes(goal.id)) {
        merged.push(goal.id)
      }
    }
    state.researchGoalsBySample[sampleId] = merged
  }

  const addSampleGoal = (sampleId: string, goalId: string) => {
    const current = state.researchGoalsBySample[sampleId] ?? []
    if (current.includes(goalId)) {
      return
    }
    state.researchGoalsBySample[sampleId] = [...current, goalId]
    const meta = researchGoalCatalogById().get(goalId)
    if (meta) {
      state.goalLabById[goalId] = { name: meta.name, lab_id: meta.lab_id, lab_name: meta.lab_name }
    }
  }

  const removeSampleGoal = (sampleId: string, goalId: string) => {
    const current = state.researchGoalsBySample[sampleId] ?? []
    const next = current.filter((id) => id !== goalId)
    state.researchGoalsBySample[sampleId] = next
    // Если убрана последняя цель лаборатории — снимаем и саму лабораторию.
    const labId = state.goalLabById[goalId]?.lab_id
    if (!labId || next.some((id) => state.goalLabById[id]?.lab_id === labId)) {
      return
    }
    const labIds = (state.labsBySample[sampleId] ?? []).map((lab) => lab.id)
    if (labIds.includes(labId)) {
      void setSampleLabs(sampleId, labIds.filter((id) => id !== labId))
    }
  }

  // Реконсиль выбранного набора целей с фактическими Research: назначить новые, удалить снятые.
  const syncSampleResearch = async (sampleId: string): Promise<boolean> => {
    const actorId = auth.user?.id ?? null
    const desired = state.researchGoalsBySample[sampleId] ?? []
    const prefix = `${sampleId}:`
    const existing = new Map<string, string>()
    for (const [key, researchId] of Object.entries(state.researchIdByKey)) {
      if (key.startsWith(prefix)) {
        existing.set(key.slice(prefix.length), researchId)
      }
    }
    let ok = true
    let changed = false
    for (const goalId of desired) {
      if (existing.has(goalId)) {
        continue
      }
      try {
        await assignSampleResearch(sampleId, goalId, actorId)
        changed = true
      } catch {
        ok = false
      }
    }
    for (const [goalId, researchId] of existing) {
      if (desired.includes(goalId)) {
        continue
      }
      try {
        await deleteResearch(researchId)
        changed = true
      } catch {
        ok = false
      }
    }
    if (changed) {
      try {
        await loadSampleResearch(sampleId)
      } catch {
        // Карта обновится при следующем входе на направление.
      }
    }
    return ok
  }

  // Сохранить одно направление: его поля, все образцы и синхронизировать цели (Research).
  const persistDirection = async (directionId: string): Promise<boolean> => {
    const direction = state.directions.find((row) => row.id === directionId)
    if (!direction) {
      return true
    }
    const okDirection = await saveDirection(direction.id, {
      year_no: direction.year_no,
      base_no: direction.base_no,
      doctor_id: direction.doctor_id,
      object_id: direction.object_id,
      is_urgent: direction.is_urgent
    })
    let okSamples = true
    const samples = state.samplesByDirection[direction.id] ?? []
    for (const sample of samples) {
      const saved = await saveSample(direction.id, sample.id, {
        name: sample.name || null,
        sample_type_id: sample.sample_type_id,
        alternate_name: sample.alternate_name || null,
        mass: sample.mass || null,
        comment: sample.comment || null,
        is_urgent: sample.is_urgent
      })
      const synced = await syncSampleResearch(sample.id)
      okSamples = okSamples && saved && synced
    }
    return okDirection && okSamples
  }

  // Пройти по всем направлениям и сохранить каждое (перед массовой регистрацией).
  const persistAll = async (): Promise<boolean> => {
    let ok = true
    for (const direction of state.directions) {
      const result = await persistDirection(direction.id)
      ok = ok && result
    }
    return ok
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
          state.registerResults[direction.id] = { ok: true, message: t('directionWizard.registeredMessage') }
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
    state.step = 'select'
    state.mode = 'select'
    state.fileType = 'xlsx'
    state.fileName = ''
    state.fileSize = 0
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
    state.labOptions = []
    state.researchGoalCatalog = []
    state.researchGoalsBySample = {}
    state.researchIdByKey = {}
    state.goalLabById = {}
    state.labsBySample = {}
    state.researchLoadedDirections = {}
    suggestionsCache.clear()
  }

  return Object.assign(state, {
    setFile,
    setFileType,
    runImport,
    loadResults,
    loadExistingDraft,
    chooseImport,
    startManual,
    addSample,
    removeSample,
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
    ensureResearchForDirection,
    applySampleTypeDefaults,
    addSampleGoal,
    removeSampleGoal,
    setSampleLabs,
    syncSampleResearch,
    persistDirection,
    persistAll,
    registerAll,
    reset
  })
}

export type DirectionWizardContext = ReturnType<typeof useDirectionWizard>
