import type { TimelineItem } from '@nuxt/ui'

// Единственный источник статусов — таблицы direction_statuses / sample_statuses
// (сид в миграции 20260303_0008): коды и русские имена совпадают с БД,
// «выдуманных» шагов в таймлайнах быть не должно.
export interface StatusStep {
  code: string
  name: string
  icon: string
}

export const DIRECTION_STATUS_FLOW: StatusStep[] = [
  { code: 'draft', name: 'Черновик', icon: 'i-lucide-file-pen-line' },
  { code: 'registered', name: 'Зарегистрировано', icon: 'i-lucide-clipboard-check' },
  { code: 'in_progress', name: 'В работе', icon: 'i-lucide-flask-conical' },
  { code: 'partially_completed', name: 'Частично выполнено', icon: 'i-lucide-circle-dashed' },
  { code: 'completed', name: 'Выполнено', icon: 'i-lucide-circle-check' }
]

export const SAMPLE_STATUS_FLOW: StatusStep[] = [
  { code: 'pending', name: 'На регистрации', icon: 'i-lucide-inbox' },
  { code: 'registered', name: 'Зарегистрирован', icon: 'i-lucide-clipboard-check' },
  { code: 'in_progress', name: 'На исследовании', icon: 'i-lucide-flask-conical' },
  { code: 'analyzed', name: 'Обработан', icon: 'i-lucide-microscope' },
  { code: 'completed', name: 'Закрыт', icon: 'i-lucide-circle-check' }
]

// Терминальная ветка образца: pending/registered → rejected (status_policy.py).
export const SAMPLE_STATUS_REJECTED: StatusStep = {
  code: 'rejected',
  name: 'Брак',
  icon: 'i-lucide-circle-x'
}

export const DIRECTION_STATUS_NAMES: Record<string, string> = Object.fromEntries(
  DIRECTION_STATUS_FLOW.map((step) => [step.code, step.name])
)

export const SAMPLE_STATUS_NAMES: Record<string, string> = Object.fromEntries(
  [...SAMPLE_STATUS_FLOW, SAMPLE_STATUS_REJECTED].map((step) => [step.code, step.name])
)

export interface StatusTimelineOptions {
  // Даты на крайних точках: начало (отбор) и конец (дедлайн выпуска).
  startDate?: string | null
  endDate?: string | null
  // Даты по конкретным статусам (если известны из истории).
  datesByCode?: Record<string, string | null | undefined>
  // «Фамилия И.О.» того, кто перевёл запись в статус (из change_log).
  actorsByCode?: Record<string, string | null | undefined>
}

// Строит элементы UTimeline из цепочки статусов. Для образца в статусе
// «Брак» цепочка обрезается до зарегистрированной части и завершается браком.
export function statusTimelineItems(
  flow: StatusStep[],
  currentCode: string | null | undefined,
  options: StatusTimelineOptions = {}
): TimelineItem[] {
  let steps = flow
  if (currentCode === SAMPLE_STATUS_REJECTED.code) {
    const reachedIndex = flow.findIndex((step) => step.code === 'registered')
    steps = [...flow.slice(0, reachedIndex + 1), SAMPLE_STATUS_REJECTED]
  }
  const lastIndex = steps.length - 1
  return steps.map((step, index) => ({
    value: step.code,
    title: step.name,
    icon: step.icon,
    description: options.actorsByCode?.[step.code] ?? undefined,
    date:
      options.datesByCode?.[step.code] ??
      (index === 0 ? options.startDate ?? undefined : undefined) ??
      (index === lastIndex ? options.endDate ?? undefined : undefined)
  }))
}
