import type { TimelineItem } from '@nuxt/ui'
import { i18n } from '@/shared/i18n'

const t = (key: string, params?: Record<string, unknown>) =>
  i18n.global.t(key, params ?? {}).toString()

// Единственный источник статусов — таблицы direction_statuses / sample_statuses
// (сид в миграции 20260303_0008): коды совпадают с БД, «выдуманных» шагов в
// таймлайнах быть не должно. Имена локализуются через statusLabels.* (i18n).
export interface StatusStep {
  code: string
  name: string
  icon: string
}

type StatusStepDef = { code: string; nameKey: string; icon: string }

const DIRECTION_STATUS_FLOW_DEFS: StatusStepDef[] = [
  { code: 'draft', nameKey: 'statusLabels.direction.draft', icon: 'i-lucide-file-pen-line' },
  { code: 'registered', nameKey: 'statusLabels.direction.registered', icon: 'i-lucide-clipboard-check' },
  { code: 'in_progress', nameKey: 'statusLabels.direction.in_progress', icon: 'i-lucide-flask-conical' },
  { code: 'partially_completed', nameKey: 'statusLabels.direction.partially_completed', icon: 'i-lucide-circle-dashed' },
  { code: 'completed', nameKey: 'statusLabels.direction.completed', icon: 'i-lucide-circle-check' }
]

const SAMPLE_STATUS_FLOW_DEFS: StatusStepDef[] = [
  { code: 'pending', nameKey: 'statusLabels.sample.pending', icon: 'i-lucide-inbox' },
  { code: 'registered', nameKey: 'statusLabels.sample.registered', icon: 'i-lucide-clipboard-check' },
  { code: 'in_progress', nameKey: 'statusLabels.sample.in_progress', icon: 'i-lucide-flask-conical' },
  { code: 'analyzed', nameKey: 'statusLabels.sample.analyzed', icon: 'i-lucide-microscope' },
  { code: 'completed', nameKey: 'statusLabels.sample.completed', icon: 'i-lucide-circle-check' }
]

// Терминальная ветка образца: pending/registered → rejected (status_policy.py).
// Код — статичная строка (не зависит от локали), вынесена отдельно для
// сравнений без резолва i18n (см. SAMPLE_STATUS_REJECTED_CODE).
export const SAMPLE_STATUS_REJECTED_CODE = 'rejected'
const SAMPLE_STATUS_REJECTED_DEF: StatusStepDef = {
  code: SAMPLE_STATUS_REJECTED_CODE,
  nameKey: 'statusLabels.sample.rejected',
  icon: 'i-lucide-circle-x'
}

const resolveStep = (def: StatusStepDef): StatusStep => ({
  code: def.code,
  name: t(def.nameKey),
  icon: def.icon
})

// Резолвятся на каждое обращение (геттеры, не константы), чтобы переключение
// языка сразу отражалось в таймлайнах/списках без перезагрузки страницы.
export const DIRECTION_STATUS_FLOW = (): StatusStep[] => DIRECTION_STATUS_FLOW_DEFS.map(resolveStep)
export const SAMPLE_STATUS_FLOW = (): StatusStep[] => SAMPLE_STATUS_FLOW_DEFS.map(resolveStep)
export const SAMPLE_STATUS_REJECTED = (): StatusStep => resolveStep(SAMPLE_STATUS_REJECTED_DEF)

export const DIRECTION_STATUS_NAMES = (): Record<string, string> => Object.fromEntries(
  DIRECTION_STATUS_FLOW().map((step) => [step.code, step.name])
)

export const SAMPLE_STATUS_NAMES = (): Record<string, string> => Object.fromEntries(
  [...SAMPLE_STATUS_FLOW(), SAMPLE_STATUS_REJECTED()].map((step) => [step.code, step.name])
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
  if (currentCode === SAMPLE_STATUS_REJECTED_CODE) {
    const reachedIndex = flow.findIndex((step) => step.code === 'registered')
    steps = [...flow.slice(0, reachedIndex + 1), SAMPLE_STATUS_REJECTED()]
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
