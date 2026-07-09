<script setup lang="ts">
import { computed } from 'vue'
import type { DirectionImportContext } from '@/modules/directions/composables/useDirectionImport'
import type { ImportIssue } from '@/modules/directions/directions.api'

const props = defineProps<{ ctx: DirectionImportContext }>()

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
    <div v-if="summary" class="flex flex-col gap-1">
      <span class="text-sm font-medium text-highlighted">Файл: {{ summary.filename }}</span>
      <div class="flex flex-wrap gap-2">
        <UBadge
          v-for="counter in counters"
          :key="counter.label"
          :color="counter.color"
          variant="subtle"
          size="lg"
          :icon="counter.icon"
          :label="`${counter.label}: ${counter.value}`"
        />
      </div>
    </div>

    <UAlert
      v-if="errors.length"
      color="error"
      variant="subtle"
      icon="i-lucide-circle-alert"
      :title="`Ошибки импорта (${errors.length})`"
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

    <UAlert
      v-if="warnings.length"
      color="warning"
      variant="subtle"
      icon="i-lucide-triangle-alert"
      :title="`Предупреждения (${warnings.length})`"
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
        Импорт не создал новых направлений. Проверьте ошибки выше.
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
            size="sm"
            :label="direction.object?.name || 'Объект не указан'"
          />
          <UBadge
            color="neutral"
            variant="outline"
            size="sm"
            :label="direction.doctor?.name || 'Врач не указан'"
          />
          <UBadge
            color="neutral"
            variant="subtle"
            size="sm"
            :label="`Образцов: ${(ctx.samplesByDirection[direction.id] || []).length}`"
          />
        </div>
        <div class="flex flex-wrap gap-2">
          <UBadge
            v-for="sample in ctx.samplesByDirection[direction.id] || []"
            :key="sample.id"
            :color="sample.name && sample.sample_type_id ? 'success' : 'warning'"
            variant="subtle"
            size="sm"
            :label="sample.name || 'Без названия'"
          />
        </div>
      </div>
    </section>
  </div>
</template>
