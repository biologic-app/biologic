<script setup lang="ts">
import { computed, ref } from 'vue'
import { VisSingleContainer, VisNestedDonut } from '@unovis/vue'
import { NestedDonut } from '@unovis/ts'
import { useLocale } from '@/shared/composables/useLocale'
import { LAB_RING_COLORS } from '@/modules/dashboard/sample-status-viz'
import { statusColorVar } from '@/shared/domain/status-color'
import { statusLabel } from '@/shared/i18n/status-label'
import type { LabStatusCount } from '@/shared/api/generated'

const props = defineProps<{
  title: string
  rows: LabStatusCount[]
  emptyLabel: string
  totalLabel: string
}>()

const { intlLocale } = useLocale()

// Drill-down: clicking a laboratory expands it to fill the whole half; clicking
// it again (or its central status) clears the selection and shows all labs.
const selectedLab = ref<string | null>(null)

const chartRows = computed(() =>
  selectedLab.value
    ? props.rows.filter((row) => row.lab_name === selectedLab.value)
    : props.rows
)

const total = computed(() => chartRows.value.reduce((sum, row) => sum + row.count, 0))
const hasData = computed(() => props.rows.length > 0)

// Two-level donut: inner ring = laboratory, outer ring = sample status.
const layers = [
  (d: LabStatusCount) => d.lab_name,
  (d: LabStatusCount) => d.status_code ?? '—'
]
const value = (d: LabStatusCount) => d.count

const layerSettings = (layer: number) => ({ width: layer === 0 ? 64 : 52 })

const labColorMap = computed(() => {
  const labs = [...new Set(props.rows.map((row) => row.lab_name))]
  return new Map(labs.map((name, index) => [name, LAB_RING_COLORS[index % LAB_RING_COLORS.length]]))
})

// Structural subset of unovis' NestedDonutSegment — depth 1 is the lab ring,
// depth 2 the status ring; data.root is the top-level lab, data.values the
// grouped source rows.
type DonutSegment = {
  depth: number
  data: { key: string; root: string; values: LabStatusCount[] }
}

const segmentColor = (segment: DonutSegment): string => {
  if (segment.depth >= 2) {
    return statusColorVar(segment.data.values[0]?.status_color)
  }
  return labColorMap.value.get(segment.data.key) ?? '#94a3b8'
}

// Inner (lab) ring is labelled by the short laboratory code; the status ring
// stays label-free and is decoded through the legend on the right.
const segmentLabel = (segment: DonutSegment): string =>
  segment.depth === 1 ? (segment.data.values[0]?.lab_code ?? segment.data.key) : ''

const events = {
  [NestedDonut.selectors.segment]: {
    click: (segment: DonutSegment) => {
      const lab = segment.data.root || segment.data.key
      selectedLab.value = selectedLab.value === lab ? null : lab
    }
  }
}

const formatNum = (n: number) => n.toLocaleString(intlLocale.value)

const centralSubLabel = computed(() => selectedLab.value ?? props.totalLabel)

const statusLegend = computed(() => {
  const seen = new Map<string, { code: string; label: string; color: string }>()
  for (const row of props.rows) {
    const key = row.status_code ?? '—'
    if (!seen.has(key)) {
      seen.set(key, {
        code: key,
        label: statusLabel('sample', row.status_code),
        color: statusColorVar(row.status_color)
      })
    }
  }
  return [...seen.values()]
})
</script>

<template>
  <UPageCard
    :aria-label="title"
    variant="subtle"
  >
    <div
      v-if="!hasData"
      class="py-10 text-center text-sm text-muted"
    >
      {{ emptyLabel }}
    </div>

    <!-- Full nested donut on the left, status legend on the right. Clicking a
         laboratory drills into it (fills the whole circle); clicking again
         returns to all labs. -->
    <div
      v-else
      class="flex flex-col items-center gap-6 sm:flex-row sm:items-center sm:justify-center sm:gap-10"
    >
      <div class="lab-donut h-[360px] w-[360px] max-w-full shrink-0">
        <VisSingleContainer :data="chartRows">
          <VisNestedDonut
            :layers="layers"
            :value="value"
            :layer-settings="layerSettings"
            :segment-color="segmentColor"
            :segment-label="segmentLabel"
            :corner-radius="3"
            :layer-padding="4"
            :central-label="formatNum(total)"
            :central-sub-label="centralSubLabel"
            :events="events"
          />
        </VisSingleContainer>
      </div>

      <div class="flex flex-col gap-2">
        <div
          v-for="status in statusLegend"
          :key="status.code"
          class="flex items-center gap-2 text-sm text-muted"
        >
          <span
            class="size-3 rounded-full inline-block shrink-0"
            :style="{ backgroundColor: status.color }"
          />
          {{ status.label }}
        </div>
      </div>
    </div>
  </UPageCard>
</template>

<style scoped>
.lab-donut {
  --vis-nested-donut-central-label-font-size: 28px;
  --vis-nested-donut-central-sublabel-font-size: 14px;
  --vis-nested-donut-central-label-text-color: var(--ui-text-highlighted);
  --vis-nested-donut-central-sublabel-text-color: var(--ui-text-muted);
  --vis-nested-donut-segment-label-text-color-light: var(--ui-text-highlighted);
}
.lab-donut :deep(path) {
  cursor: pointer;
}
</style>
