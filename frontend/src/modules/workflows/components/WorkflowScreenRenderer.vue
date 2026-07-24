<script setup lang="ts">
// components/WorkflowScreenRenderer.vue
// Грид-рендерер экрана v2 (schema-doc §3): ряды → CSS grid 12 колонок, блоки →
// col-span-{span}. Поля рендерит WorkflowFieldControl (все типы, US-005);
// секции — разделитель; table — редактируемый список строк. Скрытые поля
// (visibleWhen) не рендерятся и не участвуют в required-проверке движка.

import { watch } from 'vue'
import WorkflowFieldControl from '@/modules/workflows/components/WorkflowFieldControl.vue'
import { isVisible } from '@/modules/workflows/engine/fields'
import type {
  AnswerRow,
  Block,
  JournalAnswers,
  JournalField,
  Screen,
  Span,
  TableBlock,
} from '@/modules/workflows/types/journal'

const props = defineProps<{
  screen: Screen
  // Run id текущей записи — нужен для загрузки файлов в полях type:'file'.
  runId?: string | null
}>()

// Двусторонняя модель ответов: мутируем ключи объекта (тот же reactive-объект,
// что держит движок), поэтому reassign не нужен — v-model не эмитит событий.
const answers = defineModel<JournalAnswers>({ required: true })

// span → колоночный класс. Явная карта литеральных строк: Tailwind не видит
// динамически собранные классы, поэтому все 12 вариантов перечислены целиком.
// На мобильном блок занимает всю ширину (col-span-12), span применяется с md.
const spanClass: Record<Span, string> = {
  1: 'col-span-12 md:col-span-1',
  2: 'col-span-12 md:col-span-2',
  3: 'col-span-12 md:col-span-3',
  4: 'col-span-12 md:col-span-4',
  5: 'col-span-12 md:col-span-5',
  6: 'col-span-12 md:col-span-6',
  7: 'col-span-12 md:col-span-7',
  8: 'col-span-12 md:col-span-8',
  9: 'col-span-12 md:col-span-9',
  10: 'col-span-12 md:col-span-10',
  11: 'col-span-12 md:col-span-11',
  12: 'col-span-12 md:col-span-12',
}

function blockClass(block: Block): string {
  return spanClass[block.span]
}

// Видимо ли field-поле при текущих ответах (visibleWhen). Прочие блоки — всегда.
function isFieldVisible(field: JournalField): boolean {
  return isVisible(field, answers.value)
}

// ─── Table-блок: редактируемые строки ────────────────────────────────────────

function emptyRow(table: TableBlock): AnswerRow {
  const row: AnswerRow = {}
  for (const col of table.columns) row[col.id] = null
  return row
}

function tableRows(table: TableBlock): AnswerRow[] {
  const value = answers.value[table.fieldId]
  return Array.isArray(value) ? (value as AnswerRow[]) : []
}

function canAddRow(table: TableBlock): boolean {
  const max = table.maxRows ?? Infinity
  return tableRows(table).length < max
}

function canRemoveRow(table: TableBlock): boolean {
  return tableRows(table).length > (table.minRows ?? 0)
}

function addRow(table: TableBlock) {
  if (!canAddRow(table)) return
  answers.value[table.fieldId] = [...tableRows(table), emptyRow(table)]
}

function removeRow(table: TableBlock, index: number) {
  if (!canRemoveRow(table)) return
  answers.value[table.fieldId] = tableRows(table).filter((_, i) => i !== index)
}

// Гарантировать минимум строк на экране (minRows) для каждой table один раз при
// его появлении. Не перезаписываем уже заполненные строки (resume записи).
function seedTables(screen: Screen) {
  for (const row of screen.rows) {
    for (const block of row.blocks) {
      if (block.kind !== 'table') continue
      const table = block.table
      const existing = answers.value[table.fieldId]
      if (Array.isArray(existing)) continue
      const min = table.minRows ?? 0
      answers.value[table.fieldId] = Array.from({ length: min }, () => emptyRow(table))
    }
  }
}

watch(() => props.screen, seedTables, { immediate: true })
</script>

<template>
  <div class="flex flex-col gap-4">
    <div
      v-for="row in screen.rows"
      :key="row.id"
      class="grid grid-cols-12 gap-4"
    >
      <div
        v-for="block in row.blocks"
        :key="block.id"
        :class="blockClass(block)"
      >
        <!-- Секция-разделитель -->
        <template v-if="block.kind === 'section'">
          <div class="pt-1">
            <div class="text-sm font-semibold text-highlighted">
              {{ block.title }}
            </div>
            <p v-if="block.description" class="mt-0.5 text-xs text-muted">
              {{ block.description }}
            </p>
            <USeparator class="mt-2" />
          </div>
        </template>

        <!-- Таблица: редактируемые строки по колонкам -->
        <template v-else-if="block.kind === 'table'">
          <div class="rounded-lg border border-default p-3">
            <div class="mb-2 flex items-center gap-1.5 text-sm font-medium text-highlighted">
              <UIcon name="i-lucide-table" class="size-4 text-muted" />
              <span>{{ block.table.label }}</span>
              <UBadge
                v-if="tableRows(block.table).length"
                :label="String(tableRows(block.table).length)"
                size="xs"
                variant="subtle"
              />
            </div>

            <div class="flex flex-col gap-2.5">
              <div
                v-for="(tRow, ri) in tableRows(block.table)"
                :key="ri"
                class="rounded-md border border-default bg-elevated/30 p-2.5"
              >
                <div class="mb-1.5 flex items-center justify-between">
                  <span class="text-xs font-medium text-muted">Строка {{ ri + 1 }}</span>
                  <UButton
                    size="xs"
                    color="error"
                    variant="ghost"
                    icon="i-lucide-trash-2"
                    :disabled="!canRemoveRow(block.table)"
                    @click="removeRow(block.table, ri)"
                  />
                </div>
                <div class="grid gap-3 md:grid-cols-2">
                  <WorkflowFieldControl
                    v-for="col in block.table.columns"
                    :key="col.id"
                    v-model="tRow[col.id]"
                    :field="col"
                    :run-id="runId"
                  />
                </div>
              </div>
            </div>

            <p v-if="!tableRows(block.table).length" class="text-xs text-muted">
              Строк пока нет.
            </p>

            <UButton
              class="mt-2.5"
              size="sm"
              variant="soft"
              icon="i-lucide-plus"
              :label="block.table.addLabel ?? 'Добавить строку'"
              :disabled="!canAddRow(block.table)"
              @click="addRow(block.table)"
            />
          </div>
        </template>

        <!-- Поле (все типы — US-005). Скрытые visibleWhen не рендерятся. -->
        <template v-else-if="isFieldVisible(block.field)">
          <WorkflowFieldControl
            v-model="answers[block.field.id]"
            :field="block.field"
            :run-id="runId"
          />
        </template>
      </div>
    </div>
  </div>
</template>
