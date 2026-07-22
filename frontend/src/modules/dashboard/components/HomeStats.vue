<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useLocale } from '@/shared/composables/useLocale'
import type { DashboardKpi, DashboardSummary } from '@/modules/dashboard/types'

const props = defineProps<{
  summary: DashboardSummary | null
  loading: boolean
}>()

const { intlLocale } = useLocale()
const { t } = useI18n()

const skeletonItems = Array.from({ length: 6 }, (_, index) => index)

const kpis = computed<DashboardKpi[]>(() => props.summary?.kpis ?? [])

const formatMinutes = (value: number) => {
  if (value < 60) {
    return t('common.minutesShort', { value })
  }

  const hours = Math.floor(value / 60)
  const minutes = value % 60
  return minutes
    ? t('common.hoursMinutesShort', { hours, minutes })
    : t('common.hoursShort', { hours })
}

const formatValue = (item: DashboardKpi) => {
  if (item.unit === 'minutes') {
    return formatMinutes(item.value)
  }

  return item.value.toLocaleString(intlLocale.value)
}
</script>

<template>
  <UPageGrid class="lg:grid-cols-6 gap-4 sm:gap-6 lg:gap-px">
    <template v-if="loading && !kpis.length">
      <UPageCard
        v-for="item in skeletonItems"
        :key="item"
        variant="subtle"
        :ui="{
          container: 'gap-y-3',
          wrapper: 'items-start'
        }"
        class="lg:rounded-none first:rounded-l-lg last:rounded-r-lg"
      >
        <USkeleton class="size-10 rounded-full" />
        <USkeleton class="h-3 w-24" />
        <USkeleton class="h-7 w-20" />
      </UPageCard>
    </template>

    <template v-else>
      <UPageCard
        v-for="stat in kpis"
        :key="stat.key"
        :icon="stat.icon || 'i-lucide-chart-no-axes-column'"
        :title="stat.label"
        variant="subtle"
        :ui="{
          container: 'gap-y-1.5',
          wrapper: 'items-start',
          leading: 'p-2.5 rounded-full bg-primary/10 ring ring-inset ring-primary/25',
          title: 'font-normal text-muted text-xs uppercase'
        }"
        class="lg:rounded-none first:rounded-l-lg last:rounded-r-lg hover:z-1"
      >
        <div class="flex items-center gap-2">
          <span class="text-2xl font-semibold text-highlighted">
            {{ formatValue(stat) }}
          </span>
        </div>
      </UPageCard>
    </template>
  </UPageGrid>
</template>
