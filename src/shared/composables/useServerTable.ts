import { computed, nextTick, onMounted, ref } from 'vue'
import type { Ref, InjectionKey } from 'vue'
import type { ApiViewResponse } from '@/shared/types/api'
import type { TableFilters } from '@/shared/types/table'

export interface ServerTableOptions {
  initialPageSize?: number
  initialSort?: { field: string; order: 1 | -1 }
  sortableFields?: string[]
  filters?: TableFilters
  presetKey?: string
  settingsKey?: string
  mode?: 'paginated' | 'infinite'
  minimumLoadingMs?: number
}

export interface TablePreset {
  name: string
  filters: TableFilters
}

export interface TablePresetsApi {
  presets: Ref<TablePreset[]>
  savePreset: (name: string) => void
  applyPreset: (name: string) => void
  deletePreset: (name: string) => void
}

export const TABLE_PRESETS_KEY: InjectionKey<TablePresetsApi> = Symbol('tablePresets')

type TableQueryParams = Record<string, unknown>
const DEFAULT_PAGE_SIZE = 100
const GLOBAL_SEARCH_DEBOUNCE_MS = 500

const cloneFilters = (filters: TableFilters) => {
  const entries = Object.entries(filters).map(([key, meta]) => [key, { ...meta }])
  return Object.fromEntries(entries) as TableFilters
}

interface TableSettings {
  filters?: TableFilters
  sorting?: { field: string; order: 1 | -1 }
  pageSize?: number
  columnVisibility?: Record<string, boolean>
}

const buildPresetKey = (key?: string) =>
  key || (typeof window !== 'undefined' ? `table-presets:${window.location.pathname}` : 'table-presets')

const loadPresets = (key: string) => {
  if (typeof window === 'undefined') {
    return []
  }

  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as TablePreset[]) : []
  } catch {
    return []
  }
}

const persistPresets = (key: string, presets: TablePreset[]) => {
  if (typeof window === 'undefined') {
    return
  }

  localStorage.setItem(key, JSON.stringify(presets))
}

const loadTableSettings = (key?: string): TableSettings => {
  if (!key || typeof window === 'undefined') {
    return {}
  }

  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as TableSettings) : {}
  } catch {
    return {}
  }
}

const persistTableSettings = (key: string | undefined, patch: TableSettings) => {
  if (!key || typeof window === 'undefined') {
    return
  }

  try {
    const current = loadTableSettings(key)
    localStorage.setItem(key, JSON.stringify({ ...current, ...patch }))
  } catch {
    // Ignore storage errors so table interaction is not blocked.
  }
}

const mergeStoredFilters = (initialFilters: TableFilters, storedFilters?: TableFilters) => {
  if (!storedFilters) {
    return initialFilters
  }

  const next = cloneFilters(initialFilters)
  Object.entries(storedFilters).forEach(([key, meta]) => {
    if (key in next) {
      next[key] = { ...next[key], ...meta }
    }
  })
  return next
}

const wait = (ms: number) =>
  new Promise((resolve) => setTimeout(resolve, ms))

const resolvePageSize = (storedPageSize?: number, initialPageSize?: number) =>
  Math.max(storedPageSize ?? initialPageSize ?? DEFAULT_PAGE_SIZE, DEFAULT_PAGE_SIZE)

const isAllowedSortField = (field: string, sortableFields?: string[]) =>
  !sortableFields || !field || sortableFields.includes(field)

const resolveInitialSorting = (
  tableSettings: TableSettings,
  options: ServerTableOptions
) => {
  const storedSorting = tableSettings.sorting
  if (storedSorting && isAllowedSortField(storedSorting.field, options.sortableFields)) {
    return storedSorting
  }

  const initialSort = options.initialSort
  if (initialSort && isAllowedSortField(initialSort.field, options.sortableFields)) {
    return initialSort
  }

  return { field: '', order: 1 as const }
}

export const useServerTable = <T>(
  apiFn: (params: TableQueryParams) => Promise<ApiViewResponse<T>>,
  options: ServerTableOptions = {}
) => {
  const isInfinite = options.mode === 'infinite'
  const minimumLoadingMs = options.minimumLoadingMs ?? 350
  const tableSettings = loadTableSettings(options.settingsKey)
  const initialFilters = options.filters ?? {
    global: { value: '', matchMode: 'contains' }
  }
  const data = ref<T[]>([])
  const total = ref(0)
  const loading = ref(true)
  const error = ref(false)
  const loadingMore = ref(false)
  const pagination = ref({ page: 0, size: resolvePageSize(tableSettings.pageSize, options.initialPageSize) })
  const cursor = ref<string | null>(null)
  const nextCursor = ref<string | null>(null)
  const sorting = ref(resolveInitialSorting(tableSettings, options))
  const filters = ref<TableFilters>(mergeStoredFilters(initialFilters, tableSettings.filters))
  const lastGlobalValue = ref(filters.value.global?.value ?? '')
  const presetKey = buildPresetKey(options.presetKey)
  const presets = ref<TablePreset[]>([])

  const hasMore = computed(() => {
    if (!isInfinite) return false
    return nextCursor.value !== null
  })

  const savePreset = (name: string) => {
    if (!name.trim()) {
      return
    }

    const next = presets.value.filter((preset) => preset.name !== name)
    next.push({ name, filters: cloneFilters(filters.value) })
    presets.value = next
    persistPresets(presetKey, presets.value)
  }

  const applyPreset = (name: string) => {
    const preset = presets.value.find((item) => item.name === name)
    if (!preset) {
      return
    }

    filters.value = cloneFilters(preset.filters)
    persistTableSettings(options.settingsKey, { filters: cloneFilters(filters.value) })
    lastGlobalValue.value = filters.value.global?.value ?? ''
    pagination.value.page = 0
    cursor.value = null
    nextCursor.value = null
    fetch()
  }

  const deletePreset = (name: string) => {
    presets.value = presets.value.filter((preset) => preset.name !== name)
    persistPresets(presetKey, presets.value)
  }

  const buildParams = () => {
    const columnFilters: Record<string, unknown> = {}

    Object.entries(filters.value).forEach(([key, meta]) => {
      if (key === 'global') {
        return
      }

      const value = meta?.value
      if (Array.isArray(value)) {
        const hasValue = value.some((item) => item !== null && item !== '' && item !== undefined)
        if (hasValue) {
          columnFilters[key] = value
        }
        return
      }

      if (value !== null && value !== '' && value !== undefined) {
        columnFilters[key] = value
      }
    })

    const params: TableQueryParams = {
      limit: pagination.value.size,
      sort_by: sorting.value.field,
      sort_order: sorting.value.order === -1 ? 'desc' : 'asc'
    }

    if (isInfinite && cursor.value) {
      params.cursor = cursor.value
    }

    const global = filters.value.global?.value ?? ''
    if (global) {
      params.search = global
    }

    if (Object.keys(columnFilters).length) {
      params.filters = JSON.stringify(columnFilters)
    }

    return params
  }

  const resolveNextCursor = (response: ApiViewResponse<T>) => {
    return response.meta.nextCursor ?? null
  }

  let debounceTimer: number | undefined

  const debounceFetch = () => {
    window.clearTimeout(debounceTimer)
    debounceTimer = window.setTimeout(() => {
      fetch()
    }, GLOBAL_SEARCH_DEBOUNCE_MS)
  }

  const fetch = async () => {
    loading.value = true
    loadingMore.value = false
    error.value = false
    if (!(isInfinite && cursor.value)) {
      data.value = [] as typeof data.value
    }
    try {
      await nextTick() // let skeleton render before (potentially sync) API call
      const startedAt = performance.now()
      const response = await apiFn(buildParams())
      const remainingDelay = minimumLoadingMs - (performance.now() - startedAt)
      if (remainingDelay > 0) {
        await wait(remainingDelay)
      }
      if (isInfinite && cursor.value) {
        data.value = [...data.value, ...response.items] as typeof data.value
      } else {
        data.value = response.items as typeof data.value
      }
      total.value = response.meta.total
      nextCursor.value = resolveNextCursor(response)
    } catch {
      error.value = true
    } finally {
      loading.value = false
    }
  }

  const refresh = () => {
    pagination.value.page = 0
    cursor.value = null
    nextCursor.value = null
    fetch()
  }

  const loadMore = async () => {
    if (!isInfinite || !hasMore.value || loading.value || loadingMore.value || error.value) return
    loadingMore.value = true
    pagination.value.page += 1
    const previousCursor = cursor.value
    cursor.value = nextCursor.value
    error.value = false
    try {
      const startedAt = performance.now()
      const response = await apiFn(buildParams())
      const remainingDelay = minimumLoadingMs - (performance.now() - startedAt)
      if (remainingDelay > 0) {
        await wait(remainingDelay)
      }
      data.value = [...data.value, ...response.items] as typeof data.value
      total.value = response.meta.total
      nextCursor.value = resolveNextCursor(response)
    } catch {
      pagination.value.page -= 1
      cursor.value = previousCursor
      error.value = true
    } finally {
      loadingMore.value = false
    }
  }

  const setPage = (page: number) => {
    pagination.value.page = page
    cursor.value = null
    nextCursor.value = null
    fetch()
  }

  const setPageSize = (size: number) => {
    pagination.value.page = 0
    pagination.value.size = size
    persistTableSettings(options.settingsKey, { pageSize: size })
    cursor.value = null
    nextCursor.value = null
    fetch()
  }

  const setSort = (field: string) => {
    if (!isAllowedSortField(field, options.sortableFields)) {
      return
    }

    if (sorting.value.field === field) {
      sorting.value.order = sorting.value.order === 1 ? -1 : 1
    } else {
      sorting.value.field = field
      sorting.value.order = 1
    }
    persistTableSettings(options.settingsKey, { sorting: { ...sorting.value } })
    pagination.value.page = 0
    cursor.value = null
    nextCursor.value = null
    fetch()
  }

  const updateFilters = (nextFilters: TableFilters, debounceGlobal = false) => {
    const prevGlobal = lastGlobalValue.value
    const nextGlobal = nextFilters.global?.value ?? ''
    filters.value = nextFilters
    persistTableSettings(options.settingsKey, { filters: cloneFilters(filters.value) })
    lastGlobalValue.value = nextGlobal
    pagination.value.page = 0
    cursor.value = null
    nextCursor.value = null

    if (debounceGlobal && nextGlobal !== prevGlobal) {
      debounceFetch()
      return
    }

    fetch()
  }

  onMounted(() => {
    presets.value = loadPresets(presetKey)
  })

  return {
    data,
    total,
    loading,
    loadingMore,
    error,
    hasMore,
    pagination,
    sorting,
    filters,
    fetch,
    refresh,
    loadMore,
    setPage,
    setPageSize,
    setSort,
    updateFilters,
    presets,
    savePreset,
    applyPreset,
    deletePreset
  }
}
