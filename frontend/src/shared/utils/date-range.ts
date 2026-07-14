import { i18n } from '@/shared/i18n'

const t = (key: string, params?: Record<string, unknown>) =>
  i18n.global.t(key, params ?? {}).toString()

export type DateRangeValue = [string | null, string | null]

export interface DateRangePreset {
  label: string
  days?: number
  months?: number
  years?: number
}

export const DATE_RANGE_PRESETS: DateRangePreset[] = [
  { label: t('crud.dateRangePresets.last7Days'), days: 7 },
  { label: t('crud.dateRangePresets.last14Days'), days: 14 },
  { label: t('crud.dateRangePresets.last30Days'), days: 30 },
  { label: t('crud.dateRangePresets.last3Months'), months: 3 },
  { label: t('crud.dateRangePresets.last6Months'), months: 6 },
  { label: t('crud.dateRangePresets.lastYear'), years: 1 }
]

const pad = (value: number) => String(value).padStart(2, '0')

export const formatDateOnly = (date: Date) =>
  `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}`

const dateOnly = (date: Date) =>
  new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()))

const subtractPreset = (date: Date, preset: DateRangePreset) => {
  const next = new Date(date.getTime())
  if (preset.days) {
    next.setUTCDate(next.getUTCDate() - preset.days)
  } else if (preset.months) {
    next.setUTCMonth(next.getUTCMonth() - preset.months)
  } else if (preset.years) {
    next.setUTCFullYear(next.getUTCFullYear() - preset.years)
  }
  return next
}

export const selectDateRangePreset = (
  preset: DateRangePreset,
  currentDate = new Date()
): DateRangeValue => {
  const endDate = dateOnly(currentDate)
  const startDate = subtractPreset(endDate, preset)

  return [formatDateOnly(startDate), formatDateOnly(endDate)]
}

export const isDateRangePresetSelected = (
  value: DateRangeValue,
  preset: DateRangePreset,
  currentDate = new Date()
) => {
  const [start, end] = selectDateRangePreset(preset, currentDate)
  return value[0] === start && value[1] === end
}
