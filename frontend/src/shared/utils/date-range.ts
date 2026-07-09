export type DateRangeValue = [string | null, string | null]

export interface DateRangePreset {
  label: string
  days?: number
  months?: number
  years?: number
}

export const DATE_RANGE_PRESETS: DateRangePreset[] = [
  { label: 'За последние 7 дней', days: 7 },
  { label: 'За последние 14 дней', days: 14 },
  { label: 'За последние 30 дней', days: 30 },
  { label: 'За последние 3 месяца', months: 3 },
  { label: 'За последние 6 месяцев', months: 6 },
  { label: 'За последний год', years: 1 }
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
