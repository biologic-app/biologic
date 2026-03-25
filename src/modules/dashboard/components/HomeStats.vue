<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useLocale } from '@/shared/composables/useLocale'
import { randomInt } from '@/shared/utils/random'
import type { Period, Range, Stat } from '@/modules/dashboard/types'

const props = defineProps<{
  period: Period
  range: Range
}>()

function formatCount(value: number): string {
  return value.toLocaleString(intlLocale.value)
}

const { t } = useI18n()
const { intlLocale } = useLocale()

const baseStats = computed(() => [{
  title: t('dashboard.stats.patients'),
  icon: 'i-lucide-users',
  minValue: 120,
  maxValue: 600,
  minVariation: -10,
  maxVariation: 20
}, {
  title: t('dashboard.stats.analyses'),
  icon: 'i-lucide-flask-conical',
  minValue: 800,
  maxValue: 3000,
  minVariation: -8,
  maxVariation: 18
}, {
  title: t('dashboard.stats.critical'),
  icon: 'i-lucide-triangle-alert',
  minValue: 2,
  maxValue: 40,
  minVariation: -30,
  maxVariation: 50
}, {
  title: t('dashboard.stats.averageTime'),
  icon: 'i-lucide-timer',
  minValue: 18,
  maxValue: 72,
  minVariation: -15,
  maxVariation: 10
}])

const stats = ref<Stat[]>([])

watch([() => props.period, () => props.range, baseStats], () => {
  stats.value = baseStats.value.map((stat) => {
    const value = randomInt(stat.minValue, stat.maxValue)
    const variation = randomInt(stat.minVariation, stat.maxVariation)

    return {
      title: stat.title,
      icon: stat.icon,
      value: formatCount(value),
      variation
    }
  })
}, { immediate: true })
</script>

<template>
  <UPageGrid class="lg:grid-cols-4 gap-4 sm:gap-6 lg:gap-px">
    <UPageCard
      v-for="(stat, index) in stats"
      :key="index"
      :icon="stat.icon"
      :title="stat.title"
      to="/customers"
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
          {{ stat.value }}
        </span>

        <UBadge
          :color="stat.variation > 0 ? 'success' : 'error'"
          variant="subtle"
          class="text-xs"
        >
          {{ stat.variation > 0 ? '+' : '' }}{{ stat.variation }}%
        </UBadge>
      </div>
    </UPageCard>
  </UPageGrid>
</template>
