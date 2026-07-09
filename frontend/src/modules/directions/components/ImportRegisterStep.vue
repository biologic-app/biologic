<script setup lang="ts">
import { computed } from 'vue'
import type { DirectionImportContext } from '@/modules/directions/composables/useDirectionImport'
import type { DirectionRow } from '@/modules/directions/directions.api'

const props = defineProps<{ ctx: DirectionImportContext }>()

const directionLabel = (direction: DirectionRow) =>
  [direction.year_no, direction.base_no ? `№ ${direction.base_no}` : null].filter(Boolean).join(' ') ||
  direction.id.slice(0, 8).toUpperCase()

// Клиентская эвристика готовности (research-assignments проверяет только backend).
const isLikelyReady = (direction: DirectionRow): boolean => {
  const samples = props.ctx.samplesByDirection[direction.id] ?? []
  if (!samples.length) {
    return false
  }
  return samples.every((sample) => Boolean(sample.name) && Boolean(sample.sample_type_id))
}

const readyCount = computed(() => props.ctx.directions.filter(isLikelyReady).length)
const attentionCount = computed(() => props.ctx.directions.length - readyCount.value)

const registeredCount = computed(
  () => Object.values(props.ctx.registerResults).filter((result) => result.ok).length
)
const failedCount = computed(
  () => Object.values(props.ctx.registerResults).filter((result) => !result.ok).length
)
const hasResults = computed(() => Object.keys(props.ctx.registerResults).length > 0)

const rowState = (direction: DirectionRow) => {
  const result = props.ctx.registerResults[direction.id]
  if (result) {
    return result.ok
      ? { color: 'success' as const, label: 'Зарегистрировано', detail: '' }
      : { color: 'error' as const, label: 'Ошибка', detail: result.message }
  }
  return isLikelyReady(direction)
    ? { color: 'primary' as const, label: 'Готово к регистрации', detail: '' }
    : { color: 'warning' as const, label: 'Требует внимания', detail: 'Заполните название и тип образцов.' }
}
</script>

<template>
  <div class="flex flex-col gap-5" data-testid="direction-register-all">
    <div class="flex flex-wrap gap-2">
      <UBadge
        color="success"
        variant="subtle"
        size="lg"
        :label="`Готово: ${hasResults ? registeredCount : readyCount}`"
      />
      <UBadge
        color="warning"
        variant="subtle"
        size="lg"
        :label="`С ошибками: ${hasResults ? failedCount : attentionCount}`"
      />
      <UBadge
        color="neutral"
        variant="subtle"
        size="lg"
        :label="`Всего: ${ctx.directions.length}`"
      />
    </div>

    <div class="overflow-x-auto rounded-lg border border-default">
      <table class="w-full border-collapse text-sm">
        <thead class="bg-elevated text-left text-xs font-medium uppercase text-muted">
          <tr>
            <th class="border-b border-default px-3 py-2">
              Направление
            </th>
            <th class="border-b border-default px-3 py-2">
              Объект
            </th>
            <th class="border-b border-default px-3 py-2">
              Образцов
            </th>
            <th class="border-b border-default px-3 py-2">
              Статус
            </th>
            <th class="border-b border-default px-3 py-2">
              Причина
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="direction in ctx.directions"
            :key="direction.id"
            class="border-b border-default last:border-b-0"
            :data-testid="`direction-register-row-${direction.id}`"
          >
            <td class="px-3 py-2 align-top font-medium text-highlighted">
              {{ directionLabel(direction) }}
            </td>
            <td class="px-3 py-2 align-top text-muted">
              {{ direction.object?.name || '—' }}
            </td>
            <td class="px-3 py-2 align-top text-muted">
              {{ (ctx.samplesByDirection[direction.id] || []).length }}
            </td>
            <td class="px-3 py-2 align-top">
              <UBadge :color="rowState(direction).color" variant="subtle" :label="rowState(direction).label" />
            </td>
            <td class="px-3 py-2 align-top text-muted">
              {{ rowState(direction).detail || '—' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
