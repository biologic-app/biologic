// engine/screen.ts
// Чистая логика структурного редактора экрана v2 (schema-doc §3): добавление,
// перемещение (drag между слотами), resize span, удаление блоков и рядов, а также
// фабрики блоков палитры. Без Vue — используется ScreenEditor.vue и юнит-тестами.
// Все процедуры мутируют переданный Screen на месте (массивы через splice), чтобы
// работать и с реактивным объектом Vue, и с обычным объектом в тестах.

import type {
  Block,
  BlockKind,
  FieldType,
  JournalField,
  Row,
  Screen,
  Span,
  TableBlock,
} from '@/modules/workflows/types/journal'

export const MAX_SPAN = 12

// Монотонный счётчик + метка времени: устойчивые уникальные id даже при быстрых
// повторных вызовах (Date.now() в одиночку коллизирует внутри одного тика).
let idCounter = 0
export function genId(prefix: string): string {
  idCounter += 1
  return `${prefix}-${Date.now().toString(36)}-${idCounter.toString(36)}`
}

// ─── Палитра блоков ──────────────────────────────────────────────────────────

export interface PaletteItem {
  key: string
  kind: BlockKind
  fieldType?: FieldType // для kind: 'field'
  label: string
  icon: string
}

export interface PaletteGroup {
  label: string
  items: PaletteItem[]
}

// Дефолтная ширина блока при добавлении новым рядом: поля — половина (два в ряд),
// секции/таблицы — во всю ширину.
export function defaultSpan(kind: BlockKind): Span {
  return kind === 'field' ? 6 : 12
}

const FIELD_LABELS: Record<FieldType, string> = {
  text: 'Текстовое поле',
  number: 'Число',
  boolean: 'Флажок',
  select: 'Выбор из списка',
  date: 'Дата',
  textarea: 'Текст (многострочный)',
  dictionary: 'Справочник',
  file: 'Файл',
  computed: 'Вычисляемое поле',
}

export const PALETTE: PaletteGroup[] = [
  {
    label: 'Примитивы',
    items: [
      { key: 'text', kind: 'field', fieldType: 'text', label: 'Текст', icon: 'i-lucide-type' },
      { key: 'number', kind: 'field', fieldType: 'number', label: 'Число', icon: 'i-lucide-hash' },
      { key: 'boolean', kind: 'field', fieldType: 'boolean', label: 'Да/Нет', icon: 'i-lucide-toggle-left' },
      { key: 'select', kind: 'field', fieldType: 'select', label: 'Список', icon: 'i-lucide-list' },
      { key: 'date', kind: 'field', fieldType: 'date', label: 'Дата', icon: 'i-lucide-calendar' },
      { key: 'textarea', kind: 'field', fieldType: 'textarea', label: 'Абзац', icon: 'i-lucide-text' },
    ],
  },
  {
    label: 'Расширенные',
    items: [
      { key: 'dictionary', kind: 'field', fieldType: 'dictionary', label: 'Справочник', icon: 'i-lucide-book-marked' },
      { key: 'file', kind: 'field', fieldType: 'file', label: 'Файл', icon: 'i-lucide-paperclip' },
      { key: 'computed', kind: 'field', fieldType: 'computed', label: 'Вычисление', icon: 'i-lucide-sigma' },
    ],
  },
  {
    label: 'Разметка',
    items: [
      { key: 'section', kind: 'section', label: 'Секция', icon: 'i-lucide-heading' },
      { key: 'table', kind: 'table', label: 'Таблица', icon: 'i-lucide-table' },
    ],
  },
]

// ─── Фабрики ─────────────────────────────────────────────────────────────────

export function createField(type: FieldType): JournalField {
  const field: JournalField = { id: genId('field'), label: FIELD_LABELS[type], type }
  if (type === 'select') field.options = [{ label: 'Вариант 1', value: 'option-1' }]
  if (type === 'dictionary') field.source = { endpoint: '', labelKey: 'name', valueKey: 'id' }
  if (type === 'computed') field.expr = {}
  return field
}

export function createTable(): TableBlock {
  return {
    fieldId: genId('table'),
    label: 'Таблица',
    columns: [createField('text')],
    minRows: 0,
    addLabel: 'Добавить строку',
  }
}

// Собрать блок по элементу палитры. span задаётся вызывающим (fit-в-ряд/дефолт).
export function createBlock(item: PaletteItem, span: Span = defaultSpan(item.kind)): Block {
  const id = genId('block')
  if (item.kind === 'section') return { id, span, kind: 'section', title: 'Новая секция' }
  if (item.kind === 'table') return { id, span, kind: 'table', table: createTable() }
  return { id, span, kind: 'field', field: createField(item.fieldType ?? 'text') }
}

// ─── Span-помощники ──────────────────────────────────────────────────────────

export function clampSpan(value: number): Span {
  const v = Math.max(1, Math.min(MAX_SPAN, Math.round(value)))
  return v as Span
}

// Занятые колонки ряда (можно исключить один блок — при resize/перемещении внутри).
export function rowUsedSpan(row: Row, exceptBlockId?: string): number {
  return row.blocks.reduce((sum, b) => sum + (b.id === exceptBlockId ? 0 : b.span), 0)
}

// Свободные колонки в ряду (для fit при вставке/перемещении).
export function availableSpan(row: Row, exceptBlockId?: string): number {
  return Math.max(0, MAX_SPAN - rowUsedSpan(row, exceptBlockId))
}

// ─── Поиск ───────────────────────────────────────────────────────────────────

export interface BlockLocation {
  row: Row
  rowIndex: number
  block: Block
  blockIndex: number
}

export function findBlock(screen: Screen, blockId: string): BlockLocation | null {
  for (let ri = 0; ri < screen.rows.length; ri++) {
    const row = screen.rows[ri]
    const bi = row.blocks.findIndex((b) => b.id === blockId)
    if (bi >= 0) return { row, rowIndex: ri, block: row.blocks[bi], blockIndex: bi }
  }
  return null
}

// ─── Ряды ────────────────────────────────────────────────────────────────────

// Убрать пустые ряды (после удаления/перемещения). Splice — сохранить ссылку массива.
export function pruneEmptyRows(screen: Screen): void {
  for (let i = screen.rows.length - 1; i >= 0; i--) {
    if (screen.rows[i].blocks.length === 0) screen.rows.splice(i, 1)
  }
}

export function removeRow(screen: Screen, rowId: string): void {
  const i = screen.rows.findIndex((r) => r.id === rowId)
  if (i >= 0) screen.rows.splice(i, 1)
}

// ─── Вставка / удаление блоков ────────────────────────────────────────────────

// Вставить блок в существующий ряд перед позицией index (по умолчанию — в конец).
// span клампится к свободному месту ряда, чтобы сумма span ≤ 12.
export function insertBlockInRow(
  screen: Screen,
  rowId: string,
  block: Block,
  index?: number,
): void {
  const row = screen.rows.find((r) => r.id === rowId)
  if (!row) return
  const free = availableSpan(row)
  if (free < 1) {
    // Места нет — кладём новым рядом сразу после целевого.
    const at = screen.rows.indexOf(row) + 1
    appendBlockAsRow(screen, block, at)
    return
  }
  block.span = clampSpan(Math.min(block.span, free))
  const at = index === undefined ? row.blocks.length : Math.max(0, Math.min(index, row.blocks.length))
  row.blocks.splice(at, 0, block)
}

// Добавить блок отдельным новым рядом (в позицию atRowIndex или в конец).
export function appendBlockAsRow(screen: Screen, block: Block, atRowIndex?: number): void {
  const row: Row = { id: genId('row'), blocks: [block] }
  const at = atRowIndex === undefined ? screen.rows.length : Math.max(0, Math.min(atRowIndex, screen.rows.length))
  screen.rows.splice(at, 0, row)
}

export function removeBlock(screen: Screen, blockId: string): void {
  const loc = findBlock(screen, blockId)
  if (!loc) return
  loc.row.blocks.splice(loc.blockIndex, 1)
  pruneEmptyRows(screen)
}

// ─── Перемещение (drag между слотами) ─────────────────────────────────────────

// Изъять блок из его ряда, вернув его (или null). Пустые ряды не чистит —
// вызывающий решает, когда prune (после вставки, чтобы не сдвинуть индексы цели).
function detachBlock(screen: Screen, blockId: string): Block | null {
  const loc = findBlock(screen, blockId)
  if (!loc) return null
  loc.row.blocks.splice(loc.blockIndex, 1)
  return loc.block
}

// Переместить блок в целевой ряд на позицию index. Клампит span к свободному
// месту цели (исключая сам блок — если он уже в этом ряду, реордер).
export function moveBlockToRow(
  screen: Screen,
  blockId: string,
  targetRowId: string,
  index?: number,
): void {
  const target = screen.rows.find((r) => r.id === targetRowId)
  if (!target) return
  const block = detachBlock(screen, blockId)
  if (!block) return
  const free = Math.max(1, availableSpan(target, block.id))
  block.span = clampSpan(Math.min(block.span, free))
  const at = index === undefined ? target.blocks.length : Math.max(0, Math.min(index, target.blocks.length))
  target.blocks.splice(at, 0, block)
  pruneEmptyRows(screen)
}

// Переместить блок в новый ряд (drop в межрядный/финальный дропзон).
export function moveBlockToNewRow(screen: Screen, blockId: string, atRowIndex: number): void {
  const block = detachBlock(screen, blockId)
  if (!block) return
  // Индекс мог сдвинуться, если исходный ряд стоял раньше и опустел; prune после
  // вставки корректирует хвост, а вставку делаем по исходному atRowIndex с клампом.
  const at = Math.max(0, Math.min(atRowIndex, screen.rows.length))
  screen.rows.splice(at, 0, { id: genId('row'), blocks: [block] })
  pruneEmptyRows(screen)
}

// ─── Resize span ─────────────────────────────────────────────────────────────

// Задать span блока, не превышая свободное место ряда (сумма span ряда ≤ 12).
export function setSpan(screen: Screen, blockId: string, span: number): void {
  const loc = findBlock(screen, blockId)
  if (!loc) return
  const max = Math.max(1, availableSpan(loc.row, blockId))
  loc.block.span = clampSpan(Math.min(span, max))
}

// ─── Колонки table-блока (инспектор) ──────────────────────────────────────────

export function addColumn(table: TableBlock, type: FieldType = 'text'): void {
  table.columns.push(createField(type))
}

export function removeColumn(table: TableBlock, columnId: string): void {
  const i = table.columns.findIndex((c) => c.id === columnId)
  if (i >= 0) table.columns.splice(i, 1)
}
