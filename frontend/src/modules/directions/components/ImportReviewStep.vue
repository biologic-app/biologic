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

const directionTitle = (directionId: string, index: number) => {
  const direction = props.ctx.directions[index]
  if (direction?.year_no && direction?.base_no) {
    return `№ ${direction.year_no}-${direction.base_no}`
  }
  return `Направление ${directionId.slice(0, 8).toUpperCase()}`
}

// У врача из include нет поля `name` — ФИО собирается из отдельных полей.
// Имя и отчество сокращаем до инициалов: «Иванов И.И.».
const initial = (part: unknown): string => {
  const value = typeof part === 'string' ? part.trim() : ''
  return value ? `${value[0].toUpperCase()}.` : ''
}

const personName = (row: Record<string, unknown> | null | undefined): string => {
  if (!row) {
    return ''
  }
  const lastName = typeof row.last_name === 'string' ? row.last_name.trim() : ''
  const initials = [initial(row.first_name), initial(row.patronymic)].filter(Boolean).join('')
  const shortName = [lastName, initials].filter(Boolean).join(' ')
  return shortName || (typeof row.name === 'string' ? row.name : '')
}

const formatDate = (value: string | null | undefined): string => {
  if (!value) {
    return ''
  }
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? ''
    : date.toLocaleString('ru-RU', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
}

// Показываем первые имена образцов; остальное сворачиваем в «+N ещё».
const SAMPLE_PREVIEW_LIMIT = 4
const samplePreview = (directionId: string) => {
  const samples = props.ctx.samplesByDirection[directionId] ?? []
  return {
    total: samples.length,
    names: samples.slice(0, SAMPLE_PREVIEW_LIMIT).map((sample) => sample.name || 'Без названия'),
    rest: Math.max(0, samples.length - SAMPLE_PREVIEW_LIMIT)
  }
}
</script>

<template>
  <div class="flex flex-col gap-5">
    <section class="flex flex-col gap-3">
      <div class="flex items-center gap-2">
        <UIcon name="i-lucide-clipboard-list" class="size-4 text-muted" />
        <h3 class="text-sm font-semibold text-highlighted">
          Созданное направление
        </h3>
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
        class="rounded-lg border border-default"
        data-testid="direction-review-card"
      >
        <div class="flex flex-wrap items-center gap-2 border-b border-default bg-elevated/50 px-4 py-2.5">
          <span class="font-semibold text-highlighted">{{ directionTitle(direction.id, index) }}</span>
          <UBadge
            v-if="direction.is_urgent"
            color="error"
            variant="subtle"
            size="md"
            label="Срочное"
          />
          <UBadge
            color="neutral"
            variant="subtle"
            size="md"
            class="ml-auto"
            :label="`Образцов: ${samplePreview(direction.id).total}`"
          />
        </div>

        <dl class="grid gap-x-6 gap-y-3 px-4 py-3 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <dt class="text-xs text-muted">
              Объект
            </dt>
            <dd v-if="direction.object?.name" class="text-sm text-toned">
              {{ direction.object.name }}
            </dd>
            <dd v-else class="text-sm text-warning">
              Не указан
            </dd>
          </div>
          <div>
            <dt class="text-xs text-muted">
              Санитарный врач
            </dt>
            <dd v-if="personName(direction.doctor)" class="text-sm text-toned">
              {{ personName(direction.doctor) }}
            </dd>
            <dd v-else class="text-sm text-warning">
              Не указан
            </dd>
          </div>
          <div>
            <dt class="text-xs text-muted">
              Дата отбора
            </dt>
            <dd class="text-sm" :class="formatDate(direction.sampled_at) ? 'text-toned' : 'text-muted'">
              {{ formatDate(direction.sampled_at) || '—' }}
            </dd>
          </div>
          <div>
            <dt class="text-xs text-muted">
              Дата поступления
            </dt>
            <dd class="text-sm" :class="formatDate(direction.received_at) ? 'text-toned' : 'text-muted'">
              {{ formatDate(direction.received_at) || '—' }}
            </dd>
          </div>
        </dl>

        <div
          v-if="samplePreview(direction.id).total"
          class="flex flex-wrap items-center gap-1.5 border-t border-default px-4 py-2.5"
        >
          <UBadge
            v-for="(name, sampleIndex) in samplePreview(direction.id).names"
            :key="sampleIndex"
            color="neutral"
            variant="outline"
            size="md"
            :label="name"
          />
          <span v-if="samplePreview(direction.id).rest" class="text-xs text-muted">
            +{{ samplePreview(direction.id).rest }} ещё
          </span>
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
