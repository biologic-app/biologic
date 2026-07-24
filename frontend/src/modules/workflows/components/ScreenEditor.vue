<script setup lang="ts">
// components/ScreenEditor.vue
// Правая панель двухпанельного редактора (US-006): визуальный редактор экрана
// выбранного шага/цикла. Грид 12 колонок со слотами (schema-doc §3): палитра
// блоков, drag между слотами (нативный HTML5 DnD, как в RuleBuilder), resize span
// (drag-край + контрол), инспектор свойств блока, удаление. Чистая логика
// манипуляций — engine/screen.ts; предпросмотр переиспользует раннер-рендерер,
// чтобы результат совпадал с прохождением.

import { computed, onBeforeUnmount, ref, watch } from 'vue'
import WorkflowScreenRenderer from '@/modules/workflows/components/WorkflowScreenRenderer.vue'
import {
  MAX_SPAN,
  PALETTE,
  addColumn,
  appendBlockAsRow,
  availableSpan,
  createBlock,
  defaultSpan,
  findBlock,
  insertBlockInRow,
  moveBlockToNewRow,
  moveBlockToRow,
  removeBlock,
  removeColumn,
  removeRow,
  setSpan,
  type PaletteItem,
} from '@/modules/workflows/engine/screen'
import type {
  Block,
  FieldType,
  JournalAnswers,
  JournalField,
  Row,
  Screen,
  Span,
  TableBlock,
  ValidationRule,
} from '@/modules/workflows/types/journal'

// Экран редактируется на месте (тот же реактивный объект node.data.screen):
// мутации массивов через engine/screen.ts видит deep-watch билдера (автосейв).
const screen = defineModel<Screen>({ required: true })

// ─── Справочные подписи ──────────────────────────────────────────────────────

const FIELD_TYPE_ITEMS: Array<{ label: string, value: FieldType }> = [
  { label: 'Текст', value: 'text' },
  { label: 'Абзац', value: 'textarea' },
  { label: 'Число', value: 'number' },
  { label: 'Да/Нет', value: 'boolean' },
  { label: 'Список', value: 'select' },
  { label: 'Дата', value: 'date' },
  { label: 'Справочник', value: 'dictionary' },
  { label: 'Файл', value: 'file' },
  { label: 'Вычисление', value: 'computed' },
]

const fieldTypeLabel = (type: FieldType): string =>
  FIELD_TYPE_ITEMS.find((t) => t.value === type)?.label ?? type

const VALIDATION_KIND_ITEMS = [
  { label: 'Минимум', value: 'min' as const },
  { label: 'Максимум', value: 'max' as const },
  { label: 'Регэксп', value: 'regex' as const },
  { label: 'Макс. размер (МБ)', value: 'maxSizeMb' as const },
]

const spanItems = Array.from({ length: MAX_SPAN }, (_, i) => i + 1)

// JSON-примеры для плейсхолдеров (в атрибуте кавычки конфликтуют — держим строкой).
const EXPR_PLACEHOLDER = '{ "+": [ { "var": "a" }, { "var": "b" } ] }'
const VISIBLE_WHEN_PLACEHOLDER = '{ "==": [ { "var": "kind" }, "x" ] }'

// span → col-span без md-префикса: панель ~480px (уже md), поэтому пропорции грида
// должны применяться безусловно (у раннера — md:col-span для полноэкранной страницы).
const spanClass: Record<Span, string> = {
  1: 'col-span-1',
  2: 'col-span-2',
  3: 'col-span-3',
  4: 'col-span-4',
  5: 'col-span-5',
  6: 'col-span-6',
  7: 'col-span-7',
  8: 'col-span-8',
  9: 'col-span-9',
  10: 'col-span-10',
  11: 'col-span-11',
  12: 'col-span-12',
}

function blockTitle(block: Block): string {
  if (block.kind === 'section') return block.title || 'Секция'
  if (block.kind === 'table') return block.table.label || 'Таблица'
  return block.field.label || 'Поле'
}

function blockSubtitle(block: Block): string {
  if (block.kind === 'section') return 'Секция'
  if (block.kind === 'table') return `Таблица · ${block.table.columns.length} кол.`
  return fieldTypeLabel(block.field.type)
}

function blockIcon(block: Block): string {
  if (block.kind === 'section') return 'i-lucide-heading'
  if (block.kind === 'table') return 'i-lucide-table'
  const map: Partial<Record<FieldType, string>> = {
    text: 'i-lucide-type',
    textarea: 'i-lucide-text',
    number: 'i-lucide-hash',
    boolean: 'i-lucide-toggle-left',
    select: 'i-lucide-list',
    date: 'i-lucide-calendar',
    dictionary: 'i-lucide-book-marked',
    file: 'i-lucide-paperclip',
    computed: 'i-lucide-sigma',
  }
  return map[block.field.type] ?? 'i-lucide-square'
}

// ─── Выбор блока ─────────────────────────────────────────────────────────────

const selectedBlockId = ref<string | null>(null)

const selectedBlock = computed<Block | null>(() =>
  selectedBlockId.value ? findBlock(screen.value, selectedBlockId.value)?.block ?? null : null,
)

const selectedField = computed<JournalField | null>(() =>
  selectedBlock.value?.kind === 'field' ? selectedBlock.value.field : null,
)

const selectedTable = computed<TableBlock | null>(() =>
  selectedBlock.value?.kind === 'table' ? selectedBlock.value.table : null,
)

function select(blockId: string) {
  selectedBlockId.value = blockId
}

// ─── Drag & Drop (нативный HTML5) ────────────────────────────────────────────

type DragPayload =
  | { source: 'palette', item: PaletteItem }
  | { source: 'move', blockId: string }

const drag = ref<DragPayload | null>(null)
const dragOverKey = ref<string | null>(null)
const isDragging = computed(() => drag.value !== null)

function onPaletteDragStart(item: PaletteItem) {
  drag.value = { source: 'palette', item }
}

function onBlockDragStart(blockId: string, event: DragEvent) {
  drag.value = { source: 'move', blockId }
  event.stopPropagation()
}

function onDragEnd() {
  drag.value = null
  dragOverKey.value = null
}

// Drop на слот: вставить/переместить блок перед позицией blockIndex этого ряда.
function onDropOnSlot(row: Row, blockIndex: number, event: DragEvent) {
  event.preventDefault()
  event.stopPropagation()
  const payload = drag.value
  if (!payload) return
  if (payload.source === 'palette') {
    const block = createBlock(payload.item, defaultSpan(payload.item.kind))
    insertBlockInRow(screen.value, row.id, block, blockIndex)
    select(block.id)
  } else {
    moveBlockToRow(screen.value, payload.blockId, row.id, blockIndex)
    select(payload.blockId)
  }
  onDragEnd()
}

// Drop на фон ряда: добавить/переместить в конец ряда.
function onDropOnRow(row: Row, event: DragEvent) {
  event.preventDefault()
  const payload = drag.value
  if (!payload) return
  if (payload.source === 'palette') {
    const block = createBlock(payload.item)
    insertBlockInRow(screen.value, row.id, block)
    select(block.id)
  } else {
    moveBlockToRow(screen.value, payload.blockId, row.id)
    select(payload.blockId)
  }
  onDragEnd()
}

// Drop на межрядный/финальный дропзон: новый ряд в позицию atRowIndex.
function onDropOnNewRow(atRowIndex: number, event: DragEvent) {
  event.preventDefault()
  event.stopPropagation()
  const payload = drag.value
  if (!payload) return
  if (payload.source === 'palette') {
    const block = createBlock(payload.item)
    appendBlockAsRow(screen.value, block, atRowIndex)
    select(block.id)
  } else {
    moveBlockToNewRow(screen.value, payload.blockId, atRowIndex)
    select(payload.blockId)
  }
  onDragEnd()
}

// Клик по элементу палитры — добавить новым рядом (быстрый путь без перетаскивания).
function addFromPalette(item: PaletteItem) {
  const block = createBlock(item)
  appendBlockAsRow(screen.value, block)
  select(block.id)
}

// ─── Resize span (drag за правый край) ────────────────────────────────────────

interface ResizeState {
  blockId: string
  startX: number
  startSpan: number
  colWidth: number
}
const resizing = ref<ResizeState | null>(null)

function startResize(block: Block, event: PointerEvent) {
  event.preventDefault()
  event.stopPropagation()
  const rowEl = (event.currentTarget as HTMLElement).closest('.se-row') as HTMLElement | null
  const gridWidth = rowEl?.getBoundingClientRect().width ?? 0
  if (gridWidth <= 0) return
  resizing.value = {
    blockId: block.id,
    startX: event.clientX,
    startSpan: block.span,
    colWidth: gridWidth / MAX_SPAN,
  }
  window.addEventListener('pointermove', onResizeMove)
  window.addEventListener('pointerup', stopResize)
}

function onResizeMove(event: PointerEvent) {
  const state = resizing.value
  if (!state || state.colWidth <= 0) return
  const deltaCols = Math.round((event.clientX - state.startX) / state.colWidth)
  setSpan(screen.value, state.blockId, state.startSpan + deltaCols)
}

function stopResize() {
  resizing.value = null
  window.removeEventListener('pointermove', onResizeMove)
  window.removeEventListener('pointerup', stopResize)
}

onBeforeUnmount(stopResize)

// ─── Инспектор: span ──────────────────────────────────────────────────────────

const spanModel = computed<number>({
  get: () => selectedBlock.value?.span ?? MAX_SPAN,
  set: (value) => {
    if (selectedBlockId.value) setSpan(screen.value, selectedBlockId.value, value)
  },
})

const spanMax = computed<number>(() => {
  const id = selectedBlockId.value
  if (!id) return MAX_SPAN
  const loc = findBlock(screen.value, id)
  return loc ? Math.max(1, availableSpan(loc.row, id)) : MAX_SPAN
})

// ─── Инспектор: смена типа поля (досоздать type-специфичные слоты) ─────────────

function onFieldTypeChange(type: FieldType) {
  const field = selectedField.value
  if (!field) return
  field.type = type
  if (type === 'select' && !field.options) {
    field.options = [{ label: 'Вариант 1', value: 'option-1' }]
  }
  if (type === 'dictionary' && !field.source) {
    field.source = { endpoint: '', labelKey: 'name', valueKey: 'id' }
  }
  if (type === 'computed' && !field.expr) {
    field.expr = {}
  }
  syncJsonEditors()
}

// ─── Инспектор: select-опции ──────────────────────────────────────────────────

function addOption() {
  const field = selectedField.value
  if (!field) return
  ;(field.options ??= []).push({ label: '', value: '' })
}

function removeOption(index: number) {
  selectedField.value?.options?.splice(index, 1)
}

// ─── Инспектор: правила валидации ─────────────────────────────────────────────

function addValidation() {
  const field = selectedField.value
  if (!field) return
  ;(field.validation ??= []).push({ kind: 'min', value: 0 })
}

function removeValidation(index: number) {
  selectedField.value?.validation?.splice(index, 1)
}

// Смена типа правила заменяет объект целиком (дискриминированный union).
function changeValidationKind(index: number, kind: ValidationRule['kind']) {
  const field = selectedField.value
  if (!field?.validation) return
  const fresh: ValidationRule =
    kind === 'regex' ? { kind: 'regex', pattern: '' } : { kind, value: 0 }
  field.validation.splice(index, 1, fresh)
}

function setRuleNumber(index: number, value: number) {
  const rule = selectedField.value?.validation?.[index]
  if (rule && rule.kind !== 'regex') rule.value = value
}

function setRulePattern(index: number, pattern: string) {
  const rule = selectedField.value?.validation?.[index]
  if (rule?.kind === 'regex') rule.pattern = pattern
}

function setRuleMessage(index: number, message: string) {
  const rule = selectedField.value?.validation?.[index]
  if (rule) rule.message = message || undefined
}

// ─── Инспектор: JSON-поля (expr / visibleWhen) ────────────────────────────────

const exprText = ref('')
const exprError = ref(false)
const visibleWhenText = ref('')
const visibleWhenError = ref(false)

function syncJsonEditors() {
  const field = selectedField.value
  exprText.value = field?.expr && Object.keys(field.expr).length ? JSON.stringify(field.expr, null, 2) : ''
  visibleWhenText.value = field?.visibleWhen ? JSON.stringify(field.visibleWhen, null, 2) : ''
  exprError.value = false
  visibleWhenError.value = false
}

watch(selectedBlockId, syncJsonEditors, { immediate: true })

function commitExpr() {
  const field = selectedField.value
  if (!field) return
  const raw = exprText.value.trim()
  if (!raw) {
    field.expr = {}
    exprError.value = false
    return
  }
  try {
    field.expr = JSON.parse(raw)
    exprError.value = false
  } catch {
    exprError.value = true
  }
}

function commitVisibleWhen() {
  const field = selectedField.value
  if (!field) return
  const raw = visibleWhenText.value.trim()
  if (!raw) {
    field.visibleWhen = undefined
    visibleWhenError.value = false
    return
  }
  try {
    field.visibleWhen = JSON.parse(raw)
    visibleWhenError.value = false
  } catch {
    visibleWhenError.value = true
  }
}

// ─── Инспектор: колонки table-блока ───────────────────────────────────────────

function addTableColumn() {
  if (selectedTable.value) addColumn(selectedTable.value)
}

function removeTableColumn(columnId: string) {
  if (selectedTable.value) removeColumn(selectedTable.value, columnId)
}

// ─── Удаление ────────────────────────────────────────────────────────────────

function deleteSelected() {
  if (!selectedBlockId.value) return
  removeBlock(screen.value, selectedBlockId.value)
  selectedBlockId.value = null
}

function deleteRowByIndex(rowIndex: number) {
  const row = screen.value.rows[rowIndex]
  if (!row) return
  if (selectedBlockId.value && row.blocks.some((b) => b.id === selectedBlockId.value)) {
    selectedBlockId.value = null
  }
  removeRow(screen.value, row.id)
}

// ─── Предпросмотр (переиспользует раннер-рендерер для паритета) ────────────────

const showPreview = ref(false)
const previewAnswers = ref<JournalAnswers>({})
</script>

<template>
  <div class="flex flex-col gap-3">
    <!-- Палитра блоков -->
    <UAccordion
      :items="[{ label: 'Палитра блоков', icon: 'i-lucide-shapes', slot: 'palette', value: 'palette' }]"
      type="single"
      collapsible
      default-value="palette"
      :ui="{ item: 'border-b-0', trigger: 'py-2', body: 'pb-2' }"
    >
      <template #palette>
        <div class="flex flex-col gap-2.5">
          <p class="text-[11px] text-dimmed">
            Перетащите блок в слот/ряд ниже или нажмите, чтобы добавить новым рядом.
          </p>
          <div v-for="group in PALETTE" :key="group.label" class="flex flex-col gap-1">
            <span class="text-[10px] font-semibold uppercase tracking-wide text-dimmed">
              {{ group.label }}
            </span>
            <div class="flex flex-wrap gap-1.5">
              <UButton
                v-for="item in group.items"
                :key="item.key"
                size="xs"
                color="neutral"
                variant="soft"
                :icon="item.icon"
                :label="item.label"
                draggable="true"
                @dragstart="onPaletteDragStart(item)"
                @dragend="onDragEnd"
                @click="addFromPalette(item)"
              />
            </div>
          </div>
        </div>
      </template>
    </UAccordion>

    <USeparator />

    <!-- Инспектор выбранного блока (над канвасом — всегда виден) -->
    <div
      v-if="selectedBlock"
      class="rounded-lg border border-default bg-elevated/30 p-3"
    >
      <div class="mb-2 flex items-center justify-between">
        <div class="flex items-center gap-1.5 text-sm font-semibold text-highlighted">
          <UIcon :name="blockIcon(selectedBlock)" class="size-4 text-muted" />
          <span>{{ blockSubtitle(selectedBlock) }}</span>
        </div>
        <UButton
          size="xs"
          color="error"
          variant="ghost"
          icon="i-lucide-trash-2"
          label="Удалить блок"
          @click="deleteSelected"
        />
      </div>

      <div class="flex flex-col gap-2.5">
        <!-- Ширина (span) — общий контрол для всех блоков -->
        <UFormField label="Ширина (колонок)" size="xs">
          <USelect
            v-model="spanModel"
            :items="spanItems"
            size="xs"
            class="w-24"
          />
          <template #help>
            <span class="text-[10.5px] text-dimmed">В ряду доступно ≤ {{ spanMax }} колонок</span>
          </template>
        </UFormField>

        <!-- FIELD -->
        <template v-if="selectedField">
          <UFormField label="Подпись" size="xs">
            <UInput v-model="selectedField.label" size="xs" class="w-full" />
          </UFormField>
          <UFormField label="Тип поля" size="xs">
            <USelect
              :model-value="selectedField.type"
              :items="FIELD_TYPE_ITEMS"
              value-key="value"
              size="xs"
              class="w-full"
              @update:model-value="onFieldTypeChange"
            />
          </UFormField>
          <div class="flex items-center justify-between">
            <span class="text-xs text-muted">Обязательное</span>
            <USwitch v-model="selectedField.required" size="sm" />
          </div>
          <UFormField
            v-if="selectedField.type !== 'boolean' && selectedField.type !== 'computed'"
            label="Плейсхолдер"
            size="xs"
          >
            <UInput v-model="selectedField.placeholder" size="xs" class="w-full" />
          </UFormField>
          <UFormField label="Описание" size="xs">
            <UInput v-model="selectedField.description" size="xs" class="w-full" />
          </UFormField>

          <!-- select: опции -->
          <template v-if="selectedField.type === 'select'">
            <div class="flex items-center justify-between">
              <span class="text-xs font-medium text-muted">Опции списка</span>
              <UButton
                size="xs"
                variant="ghost"
                icon="i-lucide-plus"
                label="Опция"
                @click="addOption"
              />
            </div>
            <div
              v-for="(option, oi) in selectedField.options"
              :key="oi"
              class="flex items-center gap-1.5"
            >
              <UInput
                v-model="option.label"
                size="xs"
                placeholder="Подпись"
                class="flex-1"
              />
              <UInput
                v-model="option.value as string"
                size="xs"
                placeholder="Значение"
                class="flex-1"
              />
              <UButton
                size="xs"
                color="error"
                variant="ghost"
                icon="i-lucide-x"
                @click="removeOption(oi)"
              />
            </div>
          </template>

          <!-- dictionary: источник -->
          <template v-else-if="selectedField.type === 'dictionary' && selectedField.source">
            <UFormField label="Эндпоинт справочника" size="xs">
              <UInput
                v-model="selectedField.source.endpoint"
                size="xs"
                placeholder="employees"
                class="w-full"
              />
            </UFormField>
            <div class="grid grid-cols-2 gap-2">
              <UFormField label="labelKey" size="xs">
                <UInput v-model="selectedField.source.labelKey" size="xs" class="w-full" />
              </UFormField>
              <UFormField label="valueKey" size="xs">
                <UInput v-model="selectedField.source.valueKey" size="xs" class="w-full" />
              </UFormField>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-xs text-muted">Поиск по справочнику</span>
              <USwitch v-model="selectedField.source.searchable" size="sm" />
            </div>
          </template>

          <!-- computed: выражение json-logic -->
          <template v-else-if="selectedField.type === 'computed'">
            <UFormField
              label="Выражение (json-logic)"
              size="xs"
              :error="exprError ? 'Некорректный JSON' : undefined"
            >
              <UTextarea
                v-model="exprText"
                :rows="3"
                size="xs"
                class="w-full font-mono"
                :placeholder="EXPR_PLACEHOLDER"
                @blur="commitExpr"
              />
            </UFormField>
          </template>

          <!-- file: MIME/расширения -->
          <template v-else-if="selectedField.type === 'file'">
            <UFormField label="Принимаемые типы (accept)" size="xs">
              <UInput
                v-model="selectedField.accept"
                size="xs"
                placeholder="image/*,.pdf"
                class="w-full"
              />
            </UFormField>
          </template>

          <!-- Правила валидации -->
          <div class="flex items-center justify-between">
            <span class="text-xs font-medium text-muted">Валидация</span>
            <UButton
              size="xs"
              variant="ghost"
              icon="i-lucide-plus"
              label="Правило"
              @click="addValidation"
            />
          </div>
          <div
            v-for="(rule, ri) in selectedField.validation"
            :key="ri"
            class="flex flex-col gap-1.5 rounded-md border border-default p-2"
          >
            <div class="flex items-center gap-1.5">
              <USelect
                :model-value="rule.kind"
                :items="VALIDATION_KIND_ITEMS"
                value-key="value"
                size="xs"
                class="flex-1"
                @update:model-value="(v: ValidationRule['kind']) => changeValidationKind(ri, v)"
              />
              <UInput
                v-if="rule.kind === 'regex'"
                :model-value="rule.pattern"
                size="xs"
                placeholder="^\\d+$"
                class="flex-1"
                @update:model-value="(v: string) => setRulePattern(ri, v)"
              />
              <UInput
                v-else
                :model-value="rule.value"
                type="number"
                size="xs"
                class="w-20"
                @update:model-value="(v: number) => setRuleNumber(ri, Number(v))"
              />
              <UButton
                size="xs"
                color="error"
                variant="ghost"
                icon="i-lucide-x"
                @click="removeValidation(ri)"
              />
            </div>
            <UInput
              :model-value="rule.message"
              size="xs"
              placeholder="Текст ошибки (необязательно)"
              class="w-full"
              @update:model-value="(v: string) => setRuleMessage(ri, v)"
            />
          </div>

          <!-- visibleWhen -->
          <UFormField
            label="Видимость (visibleWhen, json-logic)"
            size="xs"
            :error="visibleWhenError ? 'Некорректный JSON' : undefined"
          >
            <UTextarea
              v-model="visibleWhenText"
              :rows="2"
              size="xs"
              class="w-full font-mono"
              :placeholder="VISIBLE_WHEN_PLACEHOLDER"
              @blur="commitVisibleWhen"
            />
          </UFormField>
        </template>

        <!-- SECTION -->
        <template v-else-if="selectedBlock.kind === 'section'">
          <UFormField label="Заголовок" size="xs">
            <UInput v-model="selectedBlock.title" size="xs" class="w-full" />
          </UFormField>
          <UFormField label="Описание" size="xs">
            <UInput v-model="selectedBlock.description" size="xs" class="w-full" />
          </UFormField>
        </template>

        <!-- TABLE -->
        <template v-else-if="selectedTable">
          <UFormField label="Название таблицы" size="xs">
            <UInput v-model="selectedTable.label" size="xs" class="w-full" />
          </UFormField>
          <UFormField label="Ключ (fieldId)" size="xs">
            <UInput v-model="selectedTable.fieldId" size="xs" class="w-full" />
          </UFormField>
          <div class="grid grid-cols-2 gap-2">
            <UFormField label="Мин. строк" size="xs">
              <UInput
                v-model.number="selectedTable.minRows"
                type="number"
                size="xs"
                class="w-full"
              />
            </UFormField>
            <UFormField label="Макс. строк" size="xs">
              <UInput
                v-model.number="selectedTable.maxRows"
                type="number"
                size="xs"
                class="w-full"
              />
            </UFormField>
          </div>
          <UFormField label="Подпись кнопки" size="xs">
            <UInput v-model="selectedTable.addLabel" size="xs" class="w-full" />
          </UFormField>

          <div class="flex items-center justify-between">
            <span class="text-xs font-medium text-muted">Колонки</span>
            <UButton
              size="xs"
              variant="ghost"
              icon="i-lucide-plus"
              label="Колонка"
              @click="addTableColumn"
            />
          </div>
          <div
            v-for="column in selectedTable.columns"
            :key="column.id"
            class="flex items-center gap-1.5"
          >
            <UInput
              v-model="column.label"
              size="xs"
              placeholder="Колонка"
              class="flex-1"
            />
            <USelect
              v-model="column.type"
              :items="FIELD_TYPE_ITEMS"
              value-key="value"
              size="xs"
              class="w-28"
            />
            <UButton
              size="xs"
              color="error"
              variant="ghost"
              icon="i-lucide-x"
              @click="removeTableColumn(column.id)"
            />
          </div>
        </template>
      </div>
    </div>

    <!-- Канвас грида -->
    <div class="se-canvas">
      <div
        v-if="!screen.rows.length"
        class="rounded-lg border border-dashed p-6 text-center transition-colors"
        :class="dragOverKey === 'empty' ? 'border-primary bg-primary/5' : 'border-default'"
        @dragover.prevent="dragOverKey = 'empty'"
        @dragleave="dragOverKey = null"
        @drop="onDropOnNewRow(0, $event)"
      >
        <UIcon name="i-lucide-layout-grid" class="mx-auto size-6 text-dimmed" />
        <p class="mt-2 text-xs text-muted">
          Экран пуст. Перетащите блок из палитры или нажмите на него.
        </p>
      </div>

      <div v-else class="flex flex-col">
        <template v-for="(row, ri) in screen.rows" :key="row.id">
          <!-- Дропзон нового ряда перед текущим -->
          <div
            class="se-newrow"
            :class="{ 'se-newrow--active': isDragging, 'se-newrow--over': dragOverKey === `nr-${ri}` }"
            @dragover.prevent="dragOverKey = `nr-${ri}`"
            @dragleave="dragOverKey = null"
            @drop="onDropOnNewRow(ri, $event)"
          />

          <!-- Ряд-грид -->
          <div class="group/row relative">
            <div
              class="se-row grid grid-cols-12 gap-2 rounded-md p-1.5"
              @dragover.prevent
              @drop="onDropOnRow(row, $event)"
            >
              <div
                v-for="(block, bi) in row.blocks"
                :key="block.id"
                :class="spanClass[block.span]"
                class="se-slot"
                @dragover.prevent="dragOverKey = block.id"
                @dragleave="dragOverKey = null"
                @drop="onDropOnSlot(row, bi, $event)"
              >
                <div
                  class="se-block"
                  :class="{
                    'se-block--selected': selectedBlockId === block.id,
                    'se-block--over': dragOverKey === block.id,
                  }"
                  @click="select(block.id)"
                >
                  <div
                    class="se-block__bar"
                    draggable="true"
                    @dragstart="onBlockDragStart(block.id, $event)"
                    @dragend="onDragEnd"
                  >
                    <UIcon name="i-lucide-grip-vertical" class="size-3.5 shrink-0 text-dimmed" />
                    <UIcon :name="blockIcon(block)" class="size-3.5 shrink-0 text-muted" />
                    <span class="truncate text-[11px] font-medium text-highlighted">
                      {{ blockTitle(block) }}
                    </span>
                    <UBadge
                      :label="`${block.span}/12`"
                      size="xs"
                      variant="subtle"
                      color="neutral"
                      class="ml-auto shrink-0"
                    />
                  </div>
                  <div class="se-block__meta">
                    {{ blockSubtitle(block) }}
                  </div>
                  <!-- Ручка resize (drag за правый край) -->
                  <div
                    class="se-block__resize"
                    title="Потяните, чтобы изменить ширину"
                    @pointerdown="startResize(block, $event)"
                    @click.stop
                  />
                </div>
              </div>
            </div>

            <UButton
              class="se-rowdel"
              size="xs"
              color="error"
              variant="ghost"
              icon="i-lucide-trash-2"
              @click="deleteRowByIndex(ri)"
            />
          </div>
        </template>

        <!-- Финальный дропзон нового ряда -->
        <div
          class="se-newrow se-newrow--tail"
          :class="{ 'se-newrow--active': isDragging, 'se-newrow--over': dragOverKey === 'nr-tail' }"
          @dragover.prevent="dragOverKey = 'nr-tail'"
          @dragleave="dragOverKey = null"
          @drop="onDropOnNewRow(screen.rows.length, $event)"
        >
          <span v-if="isDragging" class="text-[10.5px] text-dimmed">Отпустите — новый ряд</span>
        </div>
      </div>
    </div>

    <!-- Предпросмотр (тот же рендерер, что у раннера — паритет) -->
    <div class="shrink-0">
      <UButton
        block
        size="xs"
        color="neutral"
        variant="subtle"
        :icon="showPreview ? 'i-lucide-eye-off' : 'i-lucide-eye'"
        :label="showPreview ? 'Скрыть предпросмотр' : 'Предпросмотр экрана'"
        @click="showPreview = !showPreview"
      />
      <div
        v-if="showPreview"
        class="mt-2 max-h-64 overflow-y-auto rounded-lg border border-default p-3"
      >
        <WorkflowScreenRenderer
          v-if="screen.rows.length"
          v-model="previewAnswers"
          :screen="screen"
          :run-id="null"
        />
        <p v-else class="text-xs text-muted">
          Добавьте блоки, чтобы увидеть предпросмотр.
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.se-block {
  position: relative;
  border: 1.5px solid var(--ui-border);
  border-radius: 8px;
  background: var(--ui-bg);
  padding: 0 0 6px;
  cursor: pointer;
  transition: border-color 0.12s, box-shadow 0.12s;
  overflow: hidden;
}
.se-block:hover {
  border-color: color-mix(in oklab, var(--ui-primary) 40%, var(--ui-border));
}
.se-block--selected {
  border-color: var(--ui-primary);
  box-shadow: 0 0 0 1px var(--ui-primary);
}
.se-block--over {
  border-color: var(--ui-primary);
  border-style: dashed;
}
.se-block__bar {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 7px;
  background: var(--ui-bg-elevated);
  border-bottom: 1px solid var(--ui-border);
  cursor: grab;
}
.se-block__bar:active {
  cursor: grabbing;
}
.se-block__meta {
  padding: 4px 8px 0;
  font-size: 10px;
  color: var(--ui-text-dimmed);
}
.se-block__resize {
  position: absolute;
  top: 0;
  right: 0;
  width: 8px;
  height: 100%;
  cursor: col-resize;
  touch-action: none;
}
.se-block__resize:hover {
  background: color-mix(in oklab, var(--ui-primary) 30%, transparent);
}
.se-row {
  border: 1px dashed transparent;
}
.group\/row:hover .se-row {
  border-color: var(--ui-border);
}
.se-rowdel {
  position: absolute;
  top: 2px;
  right: 2px;
  opacity: 0;
  transition: opacity 0.12s;
}
.group\/row:hover .se-rowdel {
  opacity: 1;
}
.se-newrow {
  height: 6px;
  border-radius: 4px;
  transition: height 0.12s, background 0.12s;
}
.se-newrow--tail {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 22px;
  margin-top: 4px;
  border: 1px dashed var(--ui-border);
}
.se-newrow--active {
  height: 16px;
  background: color-mix(in oklab, var(--ui-primary) 8%, transparent);
}
.se-newrow--over {
  height: 24px;
  background: color-mix(in oklab, var(--ui-primary) 22%, transparent);
}
</style>
