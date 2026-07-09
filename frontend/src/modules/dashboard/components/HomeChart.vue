<script setup lang="ts">
import { computed, useTemplateRef } from 'vue'
import { format } from 'date-fns'
import { VisXYContainer, VisLine, VisAxis, VisArea, VisCrosshair, VisTooltip } from '@unovis/vue'
import { useElementSize } from '@vueuse/core'
import { useI18n } from 'vue-i18n'
import { useLocale } from '@/shared/composables/useLocale'
import type {
  DashboardLabItem,
  DashboardSampleTypeItem,
  DashboardStatusItem,
  DashboardSummary,
  Period
} from '@/modules/dashboard/types'

const cardRef = useTemplateRef<HTMLElement | null>('cardRef')

const props = defineProps<{
  period: Period
  summary: DashboardSummary | null
  loading: boolean
}>()

type DataRecord = {
  date: Date
  samplesReceived: number
  samplesCompleted: number
  samplesRejected: number
  testsCompleted: number
}

const { width } = useElementSize(cardRef)
const { t } = useI18n()
const { dateFnsLocale, intlLocale } = useLocale()

const data = computed<DataRecord[]>(() => (props.summary?.timeline ?? []).map(item => ({
  date: new Date(`${item.bucket_start}T00:00:00`),
  samplesReceived: item.samples_received,
  samplesCompleted: item.samples_completed,
  samplesRejected: item.samples_rejected,
  testsCompleted: item.tests_completed
})))

const statusItems = computed(() => props.summary?.samples_by_status ?? [])
const labItems = computed(() => props.summary?.research_by_lab ?? [])
const sampleTypeItems = computed(() => props.summary?.sample_types ?? [])

const x = (_: DataRecord, i: number) => i
const yReceived = (d: DataRecord) => d.samplesReceived
const yCompleted = (d: DataRecord) => d.samplesCompleted
const yRejected = (d: DataRecord) => d.samplesRejected

const totalReceived = computed(() => data.value.reduce((acc, d) => acc + d.samplesReceived, 0))
const totalCompleted = computed(() => data.value.reduce((acc, d) => acc + d.samplesCompleted, 0))
const totalRejected = computed(() => data.value.reduce((acc, d) => acc + d.samplesRejected, 0))

const maxStatus = computed(() => maxCount(statusItems.value))
const maxLab = computed(() => Math.max(...labItems.value.map(item => item.active_count + item.completed_count), 1))
const maxSampleType = computed(() => maxCount(sampleTypeItems.value))

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
    ${t('dashboard.chart.received')}: <b>${formatNum(d.samplesReceived)}</b><br/>
    ${t('dashboard.chart.completed')}: <b>${formatNum(d.samplesCompleted)}</b><br/>
    ${t('dashboard.chart.defective')}: <b>${formatNum(d.samplesRejected)}</b>
  </div>`

function maxCount(items: Array<DashboardStatusItem | DashboardSampleTypeItem>) {
  return Math.max(...items.map(item => item.count), 1)
}

function statusColor(item: DashboardStatusItem) {
  if (item.status_code === 'completed') return 'success'
  if (item.status_code === 'rejected') return 'error'
  if (item.status_code === 'in_progress' || item.status_code === 'analyzed') return 'primary'
  return 'neutral'
}

function labTotal(item: DashboardLabItem) {
  return item.active_count + item.completed_count
}
</script>

<template>
  <div class="space-y-6">
    <UCard ref="cardRef" :ui="{ root: 'overflow-visible', body: '!px-0 !pt-0 !pb-3' }">
      <template #header>
        <div class="flex items-start justify-between gap-6 flex-wrap">
          <div>
            <p class="text-xs text-muted uppercase mb-1.5">
              {{ t('dashboard.chart.title') }}
            </p>
            <p class="text-3xl text-highlighted font-semibold">
              {{ formatNum(totalReceived) }}
            </p>
          </div>
          <div class="flex items-start gap-6">
            <div>
              <p class="text-xs text-muted uppercase mb-1">
                {{ t('dashboard.chart.completed') }}
              </p>
              <p class="text-xl font-semibold text-success">
                {{ formatNum(totalCompleted) }}
              </p>
            </div>
            <div>
              <p class="text-xs text-muted uppercase mb-1">
                {{ t('dashboard.chart.defective') }}
              </p>
              <p class="text-xl font-semibold text-error">
                {{ formatNum(totalRejected) }}
              </p>
            </div>
          </div>
        </div>

        <div class="flex items-center gap-5 mt-3 flex-wrap">
          <div class="flex items-center gap-1.5 text-xs text-muted">
            <span class="w-6 h-0.5 rounded bg-primary inline-block" />
            {{ t('dashboard.chart.received') }}
          </div>
          <div class="flex items-center gap-1.5 text-xs text-muted">
            <span class="w-6 h-0.5 rounded bg-success inline-block" />
            {{ t('dashboard.chart.completed') }}
          </div>
          <div class="flex items-center gap-1.5 text-xs text-muted">
            <span class="w-6 h-0.5 rounded bg-error inline-block" />
            {{ t('dashboard.chart.defective') }}
          </div>
        </div>
      </template>

      <div v-if="loading && !data.length" class="h-96 px-6 py-8">
        <USkeleton class="h-full w-full" />
      </div>

      <div v-else-if="!data.length" class="h-96 flex items-center justify-center px-6">
        <p class="text-sm text-muted">
          {{ t('dashboard.empty') }}
        </p>
      </div>

      <VisXYContainer
        v-else
        :data="data"
        :padding="{ top: 40 }"
        class="h-96"
        :width="width"
      >
        <VisArea
          :x="x"
          :y="yReceived"
          color="var(--ui-primary)"
          :opacity="0.08"
        />
        <VisLine :x="x" :y="yReceived" color="var(--ui-primary)" />

        <VisArea
          :x="x"
          :y="yCompleted"
          color="var(--ui-success)"
          :opacity="0.1"
        />
        <VisLine :x="x" :y="yCompleted" color="var(--ui-success)" />

        <VisLine :x="x" :y="yRejected" color="var(--ui-error)" />

        <VisAxis type="x" :x="x" :tick-format="xTicks" />

        <VisCrosshair color="var(--ui-primary)" :template="template" />
        <VisTooltip />
      </VisXYContainer>
    </UCard>

    <div class="grid grid-cols-1 xl:grid-cols-3 gap-4 sm:gap-6">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between gap-3">
            <p class="font-medium text-highlighted">
              {{ t('dashboard.breakdowns.statuses') }}
            </p>
            <UIcon name="i-lucide-list-checks" class="size-5 text-muted" />
          </div>
        </template>

        <div class="space-y-4">
          <div v-for="item in statusItems" :key="item.status_code || item.status_name" class="space-y-1.5">
            <div class="flex items-center justify-between gap-3">
              <UBadge :color="statusColor(item)" variant="subtle">
                {{ item.status_name }}
              </UBadge>
              <span class="text-sm font-medium text-highlighted">{{ formatNum(item.count) }}</span>
            </div>
            <UProgress :model-value="item.count" :max="maxStatus" :color="statusColor(item)" />
          </div>
          <p v-if="!statusItems.length" class="text-sm text-muted">
            {{ t('dashboard.empty') }}
          </p>
        </div>
      </UCard>

      <UCard>
        <template #header>
          <div class="flex items-center justify-between gap-3">
            <p class="font-medium text-highlighted">
              {{ t('dashboard.breakdowns.labs') }}
            </p>
            <UIcon name="i-lucide-building-2" class="size-5 text-muted" />
          </div>
        </template>

        <div class="space-y-4">
          <div v-for="item in labItems" :key="item.lab_id || item.lab_name" class="space-y-1.5">
            <div class="flex items-center justify-between gap-3">
              <span class="text-sm text-default truncate">{{ item.lab_name }}</span>
              <span class="text-sm font-medium text-highlighted">{{ formatNum(labTotal(item)) }}</span>
            </div>
            <UProgress :model-value="labTotal(item)" :max="maxLab" color="primary" />
            <div class="flex items-center gap-3 text-xs text-muted">
              <span>{{ t('dashboard.breakdowns.active') }}: {{ formatNum(item.active_count) }}</span>
              <span>{{ t('dashboard.breakdowns.completed') }}: {{ formatNum(item.completed_count) }}</span>
            </div>
          </div>
          <p v-if="!labItems.length" class="text-sm text-muted">
            {{ t('dashboard.empty') }}
          </p>
        </div>
      </UCard>

      <UCard>
        <template #header>
          <div class="flex items-center justify-between gap-3">
            <p class="font-medium text-highlighted">
              {{ t('dashboard.breakdowns.sampleTypes') }}
            </p>
            <UIcon name="i-lucide-boxes" class="size-5 text-muted" />
          </div>
        </template>

        <div class="space-y-4">
          <div v-for="item in sampleTypeItems" :key="item.sample_type_id || item.sample_type_name" class="space-y-1.5">
            <div class="flex items-center justify-between gap-3">
              <span class="text-sm text-default truncate">{{ item.sample_type_name }}</span>
              <span class="text-sm font-medium text-highlighted">{{ formatNum(item.count) }}</span>
            </div>
            <UProgress :model-value="item.count" :max="maxSampleType" color="neutral" />
          </div>
          <p v-if="!sampleTypeItems.length" class="text-sm text-muted">
            {{ t('dashboard.empty') }}
          </p>
        </div>
      </UCard>
    </div>
  </div>
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
