import { ref } from 'vue'
import { apiRequest } from '@/shared/api/client.api'
import type { StatusTransitionsResponse } from '@/shared/api/generated'

// Разрешённые переходы статусов из backend (GET /api/v1/status-transitions) —
// единый источник правды для UI-схемы. Загружаем один раз на сессию и кэшируем
// на уровне модуля; компоненты используют STATIC_TRANSITIONS как фолбэк, пока
// ответ не пришёл или если запрос упал.
export type TransitionPairs = Record<string, Array<[string, string]>>

const cache = ref<TransitionPairs | null>(null)
let inflight: Promise<void> | null = null

const fetchTransitions = async (): Promise<void> => {
  const res = await apiRequest<StatusTransitionsResponse>('/status-transitions', {
    method: 'GET',
  })
  const map: TransitionPairs = {}
  for (const [resource, pairs] of Object.entries(res.data ?? {})) {
    map[resource] = pairs.map((pair) => [pair.from_code, pair.to_code])
  }
  cache.value = map
}

export const useStatusTransitions = () => {
  if (!cache.value && !inflight) {
    inflight = fetchTransitions()
      .catch(() => {
        // Фолбэк на STATIC_TRANSITIONS выполняется в компоненте.
      })
      .finally(() => {
        inflight = null
      })
  }
  return { transitions: cache }
}
