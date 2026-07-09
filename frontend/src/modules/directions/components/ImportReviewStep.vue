<script setup lang="ts">
import { computed, ref } from 'vue'
import type { DirectionImportContext } from '@/modules/directions/composables/useDirectionImport'
import type { ImportIssue } from '@/modules/directions/directions.api'

const props = defineProps<{ ctx: DirectionImportContext }>()

// Предупреждения прячем по умолчанию; ошибки импорта важны — показываем сразу
// (блок остаётся сворачиваемым, но развёрнут по умолчанию).
const showWarnings = ref(false)
const showErrors = ref(true)

const formatIssue = (issue: ImportIssue): string => {
  const parts: string[] = []
  if (typeof issue.row === 'number') {
    parts.push(`строка ${issue.row}`)
  }
  if (issue.field) {
    parts.push(String(issue.field))
  }
  const prefix = parts.length ? `${parts.join(' · ')}: ` : ''
  return `${prefix}${issue.message ?? ''}`.trim()
}

const flattenErrors = (issues: ImportIssue[]): string[] =>
  issues.flatMap((issue) => {
    if (Array.isArray(issue.errors)) {
      return issue.errors.map((nested) => formatIssue({ row: issue.row, ...nested }))
    }
    return [formatIssue(issue)]
  })

const summary = computed(() => props.ctx.summary)
const warnings = computed(() => (summary.value?.warnings ?? []).map(formatIssue).filter(Boolean))
const errors = computed(() => flattenErrors(summary.value?.errors ?? []).filter(Boolean))

const counters = computed(() => {
  const data = summary.value
  if (!data) {
    return []
  }
  return [
    { label: 'Направлений создано', value: data.directions_created, color: 'primary' as const, icon: 'i-lucide-clipboard-list' },
    { label: 'Образцов создано', value: data.samples_created, color: 'info' as const, icon: 'i-lucide-test-tube-2' },
    { label: 'Исследований создано', value: data.research_created, color: 'success' as const, icon: 'i-lucide-flask-conical' },
    { label: 'Пропущено', value: data.skipped, color: 'neutral' as const, icon: 'i-lucide-skip-forward' }
  ]
})

const directionTitle = (directionId: string, index: number) => {
  const direction = props.ctx.directions[index]
  const label = [direction?.year_no, direction?.base_no ? `№ ${direction.base_no}` : null].filter(Boolean).join(' ')
  return label || `Направление ${directionId.slice(0, 8).toUpperCase()}`
}
</script>

<template>
  <div class="flex flex-col gap-5">
    <div v-if="summary" class="flex flex-wrap gap-2">
      <UBadge
        v-for="counter in counters"
        :key="counter.label"
        :color="counter.color"
        variant="subtle"
        size="md"
        :icon="counter.icon"
        class="items-start"
      >
        <span class="line-clamp-2 break-words whitespace-normal">{{ counter.label }}: {{ counter.value }}</span>
      </UBadge>
    </div>

    <section class="flex flex-col gap-3">
      <div class="flex items-center gap-2">
        <UIcon name="i-lucide-clipboard-list" class="size-4 text-muted" />
        <h3 class="text-sm font-semibold text-highlighted">
          Созданные направления
        </h3>
        <UBadge color="neutral" variant="subtle" :label="String(ctx.directions.length)" />
      </div>

      <div v-if="ctx.loadingResults" class="flex items-center gap-2 text-sm text-muted">
        <UIcon name="i-lucide-loader-circle" class="size-4 animate-spin" />
        Загрузка созданных направлений…
      </div>

      <p v-else-if="!ctx.directions.length" class="text-sm text-muted">
        Импорт не создал новых направлений. Проверьте ошибки ниже.
      </p>

      <div
        v-for="(direction, index) in ctx.directions"
        v-else
        :key="direction.id"
        class="rounded-lg border border-default p-3"
      >
        <div class="mb-2 flex flex-wrap items-center gap-2">
          <span class="font-medium text-highlighted">{{ directionTitle(direction.id, index) }}</span>
          <UBadge
            color="neutral"
            variant="outline"
            size="lg"
            :label="direction.object?.name || 'Объект не указан'"
          />
          <UBadge
            color="neutral"
            variant="outline"
            size="lg"
            :label="direction.doctor?.name || 'Врач не указан'"
          />
          <UBadge
            color="neutral"
            variant="subtle"
            size="lg"
            :label="`Образцов: ${(ctx.samplesByDirection[direction.id] || []).length}`"
          />
        </div>
      </div>
    </section>

    <section v-if="errors.length" class="flex flex-col gap-2">
      <button
        type="button"
        class="flex w-full items-center gap-2 rounded-lg border border-default px-3 py-2 text-left text-sm font-medium text-toned hover:bg-elevated/50"
        data-testid="direction-import-errors-toggle"
        @click="showErrors = !showErrors"
      >
        <UIcon
          :name="showErrors ? 'i-lucide-chevron-down' : 'i-lucide-chevron-right'"
          class="size-4 text-muted"
        />
        <UIcon name="i-lucide-circle-alert" class="size-4 text-error" />
        <span>Ошибки ({{ errors.length }})</span>
      </button>
      <UAlert
        v-if="showErrors"
        color="error"
        variant="subtle"
        icon="i-lucide-circle-alert"
        title="Ошибки импорта"
        data-testid="direction-import-errors"
      >
        <template #description>
          <ul class="list-disc pl-4">
            <li v-for="(message, index) in errors" :key="index">
              {{ message }}
            </li>
          </ul>
        </template>
      </UAlert>
    </section>

    <section v-if="warnings.length" class="flex flex-col gap-2">
      <button
        type="button"
        class="flex w-full items-center gap-2 rounded-lg border border-default px-3 py-2 text-left text-sm font-medium text-toned hover:bg-elevated/50"
        data-testid="direction-import-warnings-toggle"
        @click="showWarnings = !showWarnings"
      >
        <UIcon
          :name="showWarnings ? 'i-lucide-chevron-down' : 'i-lucide-chevron-right'"
          class="size-4 text-muted"
        />
        <UIcon name="i-lucide-triangle-alert" class="size-4 text-warning" />
        <span>Предупреждения ({{ warnings.length }})</span>
      </button>
      <UAlert
        v-if="showWarnings"
        color="warning"
        variant="subtle"
        icon="i-lucide-triangle-alert"
        title="Предупреждения импорта"
        data-testid="direction-import-warnings"
      >
        <template #description>
          <ul class="list-disc pl-4">
            <li v-for="(message, index) in warnings" :key="index">
              {{ message }}
            </li>
          </ul>
        </template>
      </UAlert>
    </section>
  </div>
</template>
