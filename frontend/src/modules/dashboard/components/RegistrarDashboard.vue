<script setup lang="ts">
import { computed, ref, shallowRef, watch } from 'vue'
import { sub } from 'date-fns'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import type { RouteLocationRaw } from 'vue-router'
import { useLocale } from '@/shared/composables/useLocale'
import { loadRegistrarDashboard } from '@/modules/dashboard/dashboard.api'
import DashboardNavbar from '@/modules/dashboard/components/DashboardNavbar.vue'
import HomeDateRangePicker from '@/modules/dashboard/components/HomeDateRangePicker.vue'
import HomePeriodSelect from '@/modules/dashboard/components/HomePeriodSelect.vue'
import RegistrarTimelineChart from '@/modules/dashboard/components/RegistrarTimelineChart.vue'
import type { Period, Range } from '@/modules/dashboard/types'
import type { RegistrarDashboard, StatusCount } from '@/shared/api/generated'

const { t } = useI18n()
const { intlLocale } = useLocale()
const router = useRouter()

const dashboard = shallowRef<RegistrarDashboard | null>(null)
const isLoading = ref(false)
const errorMessage = ref<string | null>(null)

const range = shallowRef<Range>({
  start: sub(new Date(), { days: 14 }),
  end: new Date()
})
const period = ref<Period>('daily')
let requestSerial = 0

// --- deep links: KPI cards open the matching list, pre-filtered. The list
// pages filter by status UUID (status_id) and the is_urgent boolean, so we
// resolve status codes to their ids from the breakdown the dashboard already
// carries, and hand the list page the same JSON filter shape its table emits.

const statusId = (rows: StatusCount[] | undefined, code: string): string | undefined =>
  rows?.find((row) => row.code === code)?.id

const collectStatusIds = (rows: StatusCount[] | undefined, codes: string[]): string[] =>
  codes.map((code) => statusId(rows, code)).filter((id): id is string => Boolean(id))

const listLink = (
  name: 'directions' | 'samples',
  filters: Record<string, unknown>
): RouteLocationRaw => ({ name, query: { filters: JSON.stringify(filters) } })

const kpiCards = computed(() => {
  const data = dashboard.value
  if (!data) {
    return []
  }

  const draftDirectionId = statusId(data.directions_by_status, 'draft')
  const pendingSampleId = statusId(data.samples_by_status, 'pending')
  const openSampleIds = collectStatusIds(data.samples_by_status, [
    'registered',
    'in_progress',
    'partially_completed'
  ])

  return [
    {
      key: 'directions_draft',
      label: t('dashboard.registrar.kpi.directionsDraft'),
      value: data.kpis.directions_draft,
      icon: 'i-lucide-file-pen',
      link: draftDirectionId
        ? listLink('directions', { status_id: [draftDirectionId] })
        : undefined
    },
    {
      key: 'samples_pending',
      label: t('dashboard.registrar.kpi.samplesPending'),
      value: data.kpis.samples_pending,
      icon: 'i-lucide-inbox',
      link: pendingSampleId ? listLink('samples', { status_id: [pendingSampleId] }) : undefined
    },
    {
      key: 'urgent_open',
      label: t('dashboard.registrar.kpi.urgentOpen'),
      value: data.kpis.urgent_open,
      icon: 'i-lucide-flame',
      link: listLink('samples', {
        is_urgent: true,
        ...(openSampleIds.length ? { status_id: openSampleIds } : {})
      })
    },
    {
      key: 'directions_today',
      label: t('dashboard.registrar.kpi.directionsToday'),
      value: data.kpis.directions_received_today,
      icon: 'i-lucide-file-plus-2',
      link: undefined
    },
    {
      key: 'samples_today',
      label: t('dashboard.registrar.kpi.samplesToday'),
      value: data.kpis.samples_received_today,
      icon: 'i-lucide-package-plus',
      link: undefined
    }
  ]
})

const skeletonItems = Array.from({ length: 5 }, (_, index) => index)

const formatNumber = (value: number): string => value.toLocaleString(intlLocale.value)

watch(
  [range, period],
  async () => {
    const serial = ++requestSerial
    isLoading.value = true
    errorMessage.value = null

    try {
      const next = await loadRegistrarDashboard(range.value, period.value)
      if (serial === requestSerial) {
        dashboard.value = next
      }
    } catch (error) {
      if (serial === requestSerial) {
        errorMessage.value = error instanceof Error ? error.message : t('dashboard.error')
        dashboard.value = null
      }
    } finally {
      if (serial === requestSerial) {
        isLoading.value = false
      }
    }
  },
  { immediate: true }
)
</script>

<template>
  <UDashboardPanel id="registrar-dashboard">
    <template #header>
      <DashboardNavbar
        :title="t('dashboard.registrar.title')"
        tour-scope="dashboard"
      />

      <UDashboardToolbar>
        <template #left>
          <HomeDateRangePicker
            v-model="range"
            data-tour="dashboard-range"
            class="-ms-1"
          />

          <HomePeriodSelect
            v-model="period"
            data-tour="dashboard-period"
            :range="range"
          />
        </template>
      </UDashboardToolbar>
    </template>

    <template #body>
      <div class="flex flex-col gap-6 h-full min-h-0">
        <UAlert
          v-if="errorMessage"
          color="error"
          variant="subtle"
          icon="i-lucide-circle-alert"
          :title="t('dashboard.loadError')"
          :description="errorMessage"
        />

        <!-- KPI cards -->
        <UPageGrid class="lg:grid-cols-5 gap-4 sm:gap-6 lg:gap-px">
          <template v-if="isLoading && !kpiCards.length">
            <UPageCard
              v-for="item in skeletonItems"
              :key="item"
              variant="subtle"
              :ui="{ container: 'gap-y-3', wrapper: 'items-start' }"
              class="lg:rounded-none first:rounded-l-lg last:rounded-r-lg"
            >
              <USkeleton class="size-10 rounded-full" />
              <USkeleton class="h-3 w-24" />
              <USkeleton class="h-7 w-16" />
            </UPageCard>
          </template>

          <template v-else>
            <UPageCard
              v-for="card in kpiCards"
              :key="card.key"
              :icon="card.icon"
              :title="card.label"
              variant="subtle"
              :ui="{
                container: 'gap-y-1.5',
                wrapper: 'items-start',
                leading: 'p-2.5 rounded-full bg-primary/10 ring ring-inset ring-primary/25',
                title: 'font-normal text-muted text-xs uppercase'
              }"
              class="lg:rounded-none first:rounded-l-lg last:rounded-r-lg hover:z-1"
            >
              <div class="flex items-end justify-between gap-2 w-full">
                <span class="text-2xl font-semibold text-highlighted">
                  {{ formatNumber(card.value) }}
                </span>
                <UTooltip
                  v-if="card.link"
                  :text="t('dashboard.registrar.openList')"
                >
                  <UButton
                    icon="i-lucide-square-arrow-right-enter"
                    color="primary"
                    variant="ghost"
                    size="md"
                    :ui="{ leadingIcon: 'size-6' }"
                    :aria-label="t('dashboard.registrar.openList')"
                    @click="router.push(card.link)"
                  />
                </UTooltip>
              </div>
            </UPageCard>
          </template>
        </UPageGrid>

        <!-- Operational timeline chart — fills the remaining panel height -->
        <RegistrarTimelineChart
          class="flex-1 min-h-0"
          :timeline="dashboard?.timeline ?? []"
          :statuses="dashboard?.samples_by_status ?? []"
          :period="period"
          :loading="isLoading"
        />
      </div>
    </template>
  </UDashboardPanel>
</template>
