import { onMounted, ref } from 'vue'
import type { Ref, InjectionKey } from 'vue'
import type { ApiViewResponse } from '@/shared/types/api'
import type { TableFilters } from '@/shared/types/table'

export interface ServerTableOptions {
  initialPageSize?: number
  initialSort?: { field: string; order: 1 | -1 }
  filters?: TableFilters
  presetKey?: string
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

const cloneFilters = (filters: TableFilters) => {
  const entries = Object.entries(filters).map(([key, meta]) => [key, { ...meta }])
  return Object.fromEntries(entries) as TableFilters
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

export const useServerTable = <T>(
  apiFn: (params: Record<string, any>) => Promise<ApiViewResponse<T>>,
  options: ServerTableOptions = {}
) => {
  const data = ref<T[]>([])
  const total = ref(0)
  const loading = ref(false)
  const pagination = ref({ page: 0, size: options.initialPageSize ?? 15 })
  const sorting = ref({
    field: options.initialSort?.field ?? '',
    order: options.initialSort?.order ?? 1
  })
  const filters = ref<TableFilters>(
    options.filters ?? {
      global: { value: '', matchMode: 'contains' }
    }
  )
  const lastGlobalValue = ref(filters.value.global?.value ?? '')
  const presetKey = buildPresetKey(options.presetKey)
  const presets = ref<TablePreset[]>([])

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
    lastGlobalValue.value = filters.value.global?.value ?? ''
    pagination.value.page = 0
    fetch()
  }

  const deletePreset = (name: string) => {
    presets.value = presets.value.filter((preset) => preset.name !== name)
    persistPresets(presetKey, presets.value)
  }

  const buildParams = () => {
    const columnFilters: Record<string, any> = {}

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

    const params: Record<string, any> = {
      offset: pagination.value.page * pagination.value.size,
      limit: pagination.value.size,
      sort_by: sorting.value.field,
      sort_order: sorting.value.order === -1 ? 'desc' : 'asc'
    }

    const global = filters.value.global?.value ?? ''
    if (global) {
      params.global = global
    }

    if (Object.keys(columnFilters).length) {
      params.filters = JSON.stringify(columnFilters)
    }

    return params
  }

  let debounceTimer: number | undefined

  const debounceFetch = () => {
    window.clearTimeout(debounceTimer)
    debounceTimer = window.setTimeout(() => {
      fetch()
    }, 350)
  }

  const fetch = async () => {
    loading.value = true
    try {
      const response = await apiFn(buildParams())
      data.value = response.items
      total.value = response.meta.total
    } finally {
      loading.value = false
    }
  }

  const refresh = () => fetch()

  const setPage = (page: number) => {
    pagination.value.page = page
    fetch()
  }

  const setPageSize = (size: number) => {
    pagination.value.page = 0
    pagination.value.size = size
    fetch()
  }

  const setSort = (field: string) => {
    if (sorting.value.field === field) {
      sorting.value.order = sorting.value.order === 1 ? -1 : 1
    } else {
      sorting.value.field = field
      sorting.value.order = 1
    }

    fetch()
  }

  const updateFilters = (nextFilters: TableFilters, debounceGlobal = false) => {
    const prevGlobal = lastGlobalValue.value
    const nextGlobal = nextFilters.global?.value ?? ''
    filters.value = nextFilters
    lastGlobalValue.value = nextGlobal
    pagination.value.page = 0

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
    pagination,
    sorting,
    filters,
    fetch,
    refresh,
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
