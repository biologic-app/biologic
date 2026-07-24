// engine/convert.ts
// Детерминированный конвертер схем v1 → v2 (грид-экран). Чистый TS, без Vue.
// Контракт: docs/architecture/2026-07-22-workflow-schema-v2.md §3, §4, §7.

import type {
  JournalField,
  JournalLoopData,
  JournalNode,
  JournalSchema,
  JournalStepData,
  Row,
  Screen,
} from '@/modules/workflows/types/journal'

// Детерминированные id рядов/блоков из id поля (§7): один field → один ряд span-12.
function rowId(field: JournalField): string {
  return `row-${field.id}`
}
function blockId(field: JournalField): string {
  return `block-${field.id}`
}

// Плоский fields[] → screen: каждое поле — отдельный ряд с одним блоком span-12
// (§7.2/§7.3). Типы полей и options переходят 1:1 — новых свойств не появляется.
function fieldsToScreen(fields: JournalField[]): Screen {
  const rows: Row[] = fields.map((field) => ({
    id: rowId(field),
    blocks: [{ id: blockId(field), span: 12, kind: 'field', field }],
  }))
  return { rows }
}

// Экран узла: если он уже v2 (есть data.screen) — вернуть как есть; иначе
// собрать из плоского data.fields[] по детерминированным правилам §7.
export function toScreen(data: JournalStepData | JournalLoopData): Screen {
  if (data.screen) return data.screen
  return fieldsToScreen(data.fields ?? [])
}

// Плоский список полей экрана — top-level field-блоки в порядке рядов/блоков.
// Движок использует его для required-валидации и сводки итераций цикла.
// Колонки table-блоков сюда не входят (валидация таблиц — US-005).
export function screenFields(screen: Screen): JournalField[] {
  const out: JournalField[] = []
  for (const row of screen.rows) {
    for (const block of row.blocks) {
      if (block.kind === 'field') out.push(block.field)
    }
  }
  return out
}

// Нормализовать схему к v2: у каждого step/loop-узла появляется screen, у схемы —
// formatVersion: 2. Чистая функция: исходный объект не мутируется (возвращается
// новый). Условия/рёбра/позиции/семантика обхода не трогаются (§7.5). Идемпотентна:
// у уже-v2 узла toScreen возвращает существующий screen без изменений.
export function ensureV2(schema: JournalSchema): JournalSchema {
  const nodes: JournalNode[] = schema.nodes.map((node) => {
    if (node.type !== 'step' && node.type !== 'loop') return node
    const data = node.data as JournalStepData | JournalLoopData
    return { ...node, data: { ...data, screen: toScreen(data) } }
  })
  return { ...schema, formatVersion: 2, nodes }
}
