<script setup lang="ts">
import { computed, useTemplateRef, ref, watch } from 'vue'
import { eachDayOfInterval, eachWeekOfInterval, eachMonthOfInterval, format } from 'date-fns'
import { VisXYContainer, VisLine, VisAxis, VisArea, VisCrosshair, VisTooltip } from '@unovis/vue'
import { useElementSize } from '@vueuse/core'
import { useI18n } from 'vue-i18n'
import { useLocale } from '@/shared/composables/useLocale'
import type { Period, Range } from '@/modules/dashboard/types'

const cardRef = useTemplateRef<HTMLElement | null>('cardRef')

const props = defineProps<{
  period: Period
  range: Range
}>()

type DataRecord = {
  date: Date
  total: number
  defective: number
}

const { width } = useElementSize(cardRef)
const { t } = useI18n()
const { dateFnsLocale, intlLocale } = useLocale()

const data = ref<DataRecord[]>([])

watch([() => props.period, () => props.range], () => {
  const dates = ({
    daily: eachDayOfInterval,
    weekly: eachWeekOfInterval,
    monthly: eachMonthOfInterval
  } as Record<Period, typeof eachDayOfInterval>)[props.period](props.range)

  data.value = dates.map(date => {
    const total = Math.floor(Math.random() * 9000) + 1000
    const defective = Math.floor(total * (Math.random() * 0.08 + 0.01))
    return { date, total, defective }
  })
}, { immediate: true })

const x = (_: DataRecord, i: number) => i
const yTotal = (d: DataRecord) => d.total
const yDefective = (d: DataRecord) => d.defective

const totalSamples = computed(() => data.value.reduce((acc, d) => acc + d.total, 0))
const totalDefective = computed(() => data.value.reduce((acc, d) => acc + d.defective, 0))

const formatNum = (n: number) => n.toLocaleString(intlLocale.value)

const formatDate = (date: Date): string => ({
  daily: format(date, 'd MMM', { locale: dateFnsLocale.value }),
  weekly: format(date, 'd MMM', { locale: dateFnsLocale.value }),
  monthly: format(date, 'MMM yyyy', { locale: dateFnsLocale.value })
})[props.period]

const xTicks = (i: number) => {
  if (i === 0 || i === data.value.length - 1 || !data.value[i]) return ''
  return formatDate(data.value[i].date)
}

const template = (d: DataRecord) =>
  `<div style="font-size:13px;line-height:1.8">
    <b>${formatDate(d.date)}</b><br/>
    ${t('dashboard.chart.total')}: <b>${formatNum(d.total)}</b><br/>
    <span style="color:#f87171">${t('dashboard.chart.defective')}: <b>${formatNum(d.defective)}</b></span>
  </div>`
</script>

<template>
  <UCard ref="cardRef" :ui="{ root: 'overflow-visible', body: '!px-0 !pt-0 !pb-3' }">
    <template #header>
      <div class="flex items-start justify-between gap-6 flex-wrap">
        <div>
          <p class="text-xs text-muted uppercase mb-1.5">{{ t('dashboard.chart.title') }}</p>
          <p class="text-3xl text-highlighted font-semibold">{{ formatNum(totalSamples) }}</p>
        </div>
        <div>
          <p class="text-xs text-muted uppercase mb-1">{{ t('dashboard.chart.defective') }}</p>
          <p class="text-xl font-semibold text-red-400">{{ formatNum(totalDefective) }}</p>
        </div>
      </div>

      <div class="flex items-center gap-5 mt-3">
        <div class="flex items-center gap-1.5 text-xs text-muted">
          <span class="w-6 h-0.5 rounded bg-[var(--ui-primary)] inline-block" />
          {{ t('dashboard.chart.totalSamples') }}
        </div>
        <div class="flex items-center gap-1.5 text-xs text-muted">
          <span class="w-6 h-0.5 rounded bg-red-400 inline-block" />
          {{ t('dashboard.chart.defective') }}
        </div>
      </div>
    </template>

    <VisXYContainer :data="data" :padding="{ top: 40 }" class="h-96" :width="width">
      <VisArea :x="x" :y="yTotal" color="var(--ui-primary)" :opacity="0.08" />
      <VisLine :x="x" :y="yTotal" color="var(--ui-primary)" />

      <VisArea :x="x" :y="yDefective" color="#f87171" :opacity="0.12" />
      <VisLine :x="x" :y="yDefective" color="#f87171" />

      <VisAxis type="x" :x="x" :tick-format="xTicks" />

      <VisCrosshair color="var(--ui-primary)" :template="template" />
      <VisTooltip />
    </VisXYContainer>
  </UCard>
</template>

<style scoped>
.unovis-xy-container {
  --vis-crosshair-line-stroke-color: var(--ui-primary);
  --vis-crosshair-circle-stroke-color: var(--ui-bg);
  --vis-axis-grid-color: var(--ui-border);
  --vis-axis-tick-color: var(--ui-border);
  --vis-axis-tick-label-color: var(--ui-text-dimmed);
  --vis-tooltip-background-color: var(--ui-bg);
  --vis-tooltip-border-color: var(--ui-border);
  --vis-tooltip-text-color: var(--ui-text-highlighted);
}
</style>
