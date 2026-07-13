<script setup lang="ts">
import { computed, useTemplateRef } from 'vue'
import { format } from 'date-fns'
import { VisXYContainer, VisStackedBar, VisAxis, VisCrosshair, VisTooltip } from '@unovis/vue'
import { useElementSize } from '@vueuse/core'
import { useI18n } from 'vue-i18n'
import { useLocale } from '@/shared/composables/useLocale'
import { sampleStatusOrder } from '@/modules/dashboard/sample-status-viz'
import { statusColorVar } from '@/shared/domain/status-color'
import type { Period } from '@/modules/dashboard/types'
import type { StatusCount, TimelineBucket } from '@/shared/api/generated'

const props = defineProps<{
  timeline: TimelineBucket[]
  statuses: StatusCount[]
  period: Period
  loading: boolean
}>()

const cardRef = useTemplateRef<HTMLElement | null>('cardRef')
const { width } = useElementSize(cardRef)
const { t } = useI18n()
const { dateFnsLocale, intlLocale } = useLocale()

type Series = { code: string; name: string; color: string }
type DataRecord = { date: Date; byStatus: Record<string, number> }

// One stacked series per sample status, in lifecycle order, coloured from the
// shared palette (in_progress sky-blue, rejected red).
const series = computed<Series[]>(() =>
  props.statuses
    .filter((status): status is StatusCount & { code: string } => Boolean(status.code))
    .slice()
    .sort((a, b) => sampleStatusOrder(a.code) - sampleStatusOrder(b.code))
    .map((status) => ({ code: status.code, name: status.name, color: statusColorVar(status.color) }))
)

const data = computed<DataRecord[]>(() =>
  props.timeline.map((bucket) => ({
    date: new Date(`${bucket.bucket_start}T00:00:00`),
    byStatus: bucket.by_status
  }))
)

const x = (_: DataRecord, index: number) => index
const y = computed(() => series.value.map((s) => (d: DataRecord) => d.byStatus[s.code] ?? 0))
const barColors = computed(() => series.value.map((s) => s.color))

const sumByCode = (code: string) =>
  data.value.reduce((sum, d) => sum + (d.byStatus[code] ?? 0), 0)

const totalReceived = computed(() =>
  data.value.reduce((sum, d) => sum + Object.values(d.byStatus).reduce((a, b) => a + b, 0), 0)
)
const totalCompleted = computed(() => sumByCode('completed'))
const totalRejected = computed(() => sumByCode('rejected'))

const formatNum = (value: number) => value.toLocaleString(intlLocale.value)

const formatDate = (date: Date): string =>
  ({
    daily: format(date, 'd MMM', { locale: dateFnsLocale.value }),
    weekly: format(date, 'd MMM', { locale: dateFnsLocale.value }),
    monthly: format(date, 'MMM yyyy', { locale: dateFnsLocale.value })
  })[props.period]

const xTickFormat = (index: number) => {
  const record = data.value[Math.round(index)]
  if (!record) {
    return ''
  }
  const step = Math.max(Math.ceil(data.value.length / 8), 1)
  return Math.round(index) % step === 0 ? formatDate(record.date) : ''
}

const yTickFormat = (value: number) => (Number.isInteger(value) ? formatNum(value) : '')

const template = (d: DataRecord) => {
  const lines = series.value
    .filter((s) => (d.byStatus[s.code] ?? 0) > 0)
    .map(
      (s) =>
        `<div><span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${s.color};margin-right:6px"></span>${s.name}: <b>${formatNum(d.byStatus[s.code] ?? 0)}</b></div>`
    )
    .join('')
  return `<div style="font-size:13px;line-height:1.7"><b>${formatDate(d.date)}</b>${lines || '<div>—</div>'}</div>`
}
</script>

<template>
  <UCard
    ref="cardRef"
    :ui="{ root: 'overflow-visible flex flex-col', body: '!px-2 !pt-0 !pb-3 flex-1 min-h-0 flex flex-col' }"
  >
    <template #header>
      <div class="flex items-start justify-between gap-6 flex-wrap">
        <div>
          <p class="text-xs text-muted uppercase mb-1.5">
            {{ t('dashboard.registrar.chart.title') }}
          </p>
          <p class="text-3xl text-highlighted font-semibold">
            {{ formatNum(totalReceived) }}
          </p>
        </div>
        <div class="flex items-start gap-6">
          <div>
            <p class="text-xs text-muted uppercase mb-1">
              {{ t('dashboard.registrar.chart.completed') }}
            </p>
            <p class="text-xl font-semibold text-success">
              {{ formatNum(totalCompleted) }}
            </p>
          </div>
          <div>
            <p class="text-xs text-muted uppercase mb-1">
              {{ t('dashboard.registrar.chart.rejected') }}
            </p>
            <p class="text-xl font-semibold text-error">
              {{ formatNum(totalRejected) }}
            </p>
          </div>
        </div>
      </div>

      <div class="flex items-center gap-x-5 gap-y-1.5 mt-3 flex-wrap">
        <div
          v-for="item in series"
          :key="item.code"
          class="flex items-center gap-1.5 text-xs text-muted"
        >
          <span
            class="size-2.5 rounded-sm inline-block"
            :style="{ backgroundColor: item.color }"
          />
          {{ item.name }}
        </div>
      </div>
    </template>

    <div
      v-if="loading && !data.length"
      class="flex-1 min-h-0 px-6 py-8"
    >
      <USkeleton class="h-full w-full" />
    </div>

    <div
      v-else-if="!data.length"
      class="flex-1 min-h-0 flex items-center justify-center px-6"
    >
      <p class="text-sm text-muted">
        {{ t('dashboard.empty') }}
      </p>
    </div>

    <VisXYContainer
      v-else
      :data="data"
      :width="width"
      class="flex-1 min-h-0 w-full"
      :margin="{ top: 12, right: 12, bottom: 8, left: 12 }"
    >
      <VisStackedBar
        :x="x"
        :y="y"
        :color="barColors"
        :rounded-corners="3"
        :bar-padding="0.25"
      />
      <VisAxis
        type="x"
        :x="x"
        :tick-format="xTickFormat"
        :grid-line="false"
        :tick-line="false"
        :domain-line="false"
      />
      <VisAxis
        type="y"
        :tick-format="yTickFormat"
        :num-ticks="4"
        :domain-line="false"
        :tick-line="false"
      />
      <VisCrosshair
        color="var(--ui-primary)"
        :template="template"
      />
      <VisTooltip />
    </VisXYContainer>
  </UCard>
</template>

<style scoped>
.unovis-xy-container {
  --vis-crosshair-line-stroke-color: var(--ui-border);
  --vis-crosshair-circle-stroke-color: var(--ui-bg);
  --vis-axis-grid-color: var(--ui-border);
  --vis-axis-tick-color: transparent;
  --vis-axis-tick-label-color: var(--ui-text-dimmed);
  --vis-tooltip-background-color: var(--ui-bg);
  --vis-tooltip-border-color: var(--ui-border);
  --vis-tooltip-text-color: var(--ui-text-highlighted);
}
</style>
