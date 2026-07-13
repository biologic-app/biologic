<script setup lang="ts">
import { computed, reactive } from 'vue'
import type { DirectionWizardContext } from '@/modules/directions/composables/useDirectionWizard'
import type { DirectionRow } from '@/modules/directions/directions.api'

const props = defineProps<{ ctx: DirectionWizardContext }>()

const directionLabel = (direction: DirectionRow) =>
  direction.year_no && direction.base_no
    ? `№ ${direction.year_no}-${direction.base_no}`
    : direction.id.slice(0, 8).toUpperCase()

// Образцы направления, которым не хватает данных для регистрации (нужны название и тип).
const incompleteSamples = (direction: DirectionRow) => {
  const samples = props.ctx.samplesByDirection[direction.id] ?? []
  return samples
    .map((sample, index) => ({ sample, index }))
    .filter(({ sample }) => !sample.name || !sample.sample_type_id)
}

// Клиентская эвристика готовности (research-assignments проверяет только backend).
const isLikelyReady = (direction: DirectionRow): boolean => {
  const samples = props.ctx.samplesByDirection[direction.id] ?? []
  if (!samples.length) {
    return false
  }
  return incompleteSamples(direction).length === 0
}

// Направления, которые нельзя зарегистрировать сейчас — с перечнем проблемных образцов.
const blockedDirections = computed(() =>
  props.ctx.directions
    .filter((direction) => !props.ctx.registerResults[direction.id]?.ok && !isLikelyReady(direction))
    .map((direction) => ({ direction, samples: incompleteSamples(direction) }))
)

// Список проблемных образцов свёрнут по умолчанию (тот же паттерн, что и в предупреждениях импорта).
const expandedWarnings = reactive<Record<string, boolean>>({})
const toggleWarning = (directionId: string) => {
  expandedWarnings[directionId] = !expandedWarnings[directionId]
}

const rowState = (direction: DirectionRow) => {
  const result = props.ctx.registerResults[direction.id]
  if (result) {
    return result.ok
      ? { color: 'success' as const, label: 'Зарегистрировано', detail: '' }
      : { color: 'error' as const, label: 'Ошибка', detail: result.message }
  }
  // До нажатия «Зарегистрировать» направление остаётся черновиком.
  return isLikelyReady(direction)
    ? { color: 'neutral' as const, label: 'Черновик — готово к регистрации', detail: '' }
    : { color: 'warning' as const, label: 'Черновик — требует внимания', detail: 'Заполните название и тип образцов.' }
}
</script>

<template>
  <div class="flex flex-col gap-5" data-testid="direction-register-all">
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

    <section
      v-for="{ direction, samples } in blockedDirections"
      :key="direction.id"
      class="flex flex-col gap-2"
    >
      <button
        type="button"
        class="flex w-full items-center gap-2 rounded-lg border border-default px-3 py-2 text-left text-sm font-medium text-toned hover:bg-elevated/50"
        data-testid="direction-register-warning-toggle"
        @click="toggleWarning(direction.id)"
      >
        <UIcon
          :name="expandedWarnings[direction.id] ? 'i-lucide-chevron-down' : 'i-lucide-chevron-right'"
          class="size-4 text-muted"
        />
        <UIcon name="i-lucide-triangle-alert" class="size-4 text-warning" />
        <span>{{ directionLabel(direction) }} не может быть зарегистрировано ({{ samples.length }})</span>
      </button>
      <UAlert
        v-if="expandedWarnings[direction.id]"
        color="warning"
        variant="subtle"
        icon="i-lucide-triangle-alert"
        :title="`${directionLabel(direction)} не может быть зарегистрировано`"
        data-testid="direction-register-warning"
      >
        <template #description>
          <p class="mb-1">
            Заполните название и тип у образцов:
          </p>
          <ul class="list-inside list-disc">
            <li v-for="{ sample, index } in samples" :key="sample.id">
              Образец {{ index + 1 }}: {{ sample.name || 'без названия' }}
              <template v-if="!sample.sample_type_id">
                — не указан тип
              </template>
            </li>
          </ul>
        </template>
      </UAlert>
    </section>
  </div>
</template>
