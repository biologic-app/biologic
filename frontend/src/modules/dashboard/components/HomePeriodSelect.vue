<script setup lang="ts">
import { computed, watch } from 'vue'
import { eachDayOfInterval } from 'date-fns'
import { useI18n } from 'vue-i18n'
import type { Period, Range } from '@/modules/dashboard/types'

const model = defineModel<Period>({ required: true })
const { t } = useI18n()

const props = defineProps<{
  range: Range
}>()

const days = computed(() => eachDayOfInterval(props.range))

const periods = computed<Period[]>(() => {
  if (days.value.length <= 8) {
    return ['daily']
  }

  if (days.value.length <= 31) {
    return ['daily', 'weekly']
  }

  return ['weekly', 'monthly']
})

watch(periods, () => {
  if (!periods.value.includes(model.value)) {
    model.value = periods.value[0]
  }
})

const items = computed(() => periods.value.map(period => ({
  label: t(`dashboard.periods.${period}`),
  value: period
})))
</script>

<template>
  <USelect
    v-model="model"
    :items="items"
    variant="ghost"
    class="data-[state=open]:bg-elevated"
    :ui="{ value: 'capitalize', itemLabel: 'capitalize', trailingIcon: 'group-data-[state=open]:rotate-180 transition-transform duration-200' }"
  />
</template>
