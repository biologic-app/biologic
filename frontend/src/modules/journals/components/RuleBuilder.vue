<script setup lang="ts">
// components/journal/RuleBuilder.vue
// Графический конструктор правил json-logic — рекурсивные блоки

import { computed, defineComponent, h, ref, watch, type VNode } from 'vue';
import type { JournalConditionData } from '@/modules/journals/types/journal';

const props = defineProps<{
  modelValue: JournalConditionData['rule']
}>()
const emit = defineEmits<{
  'update:modelValue': [JournalConditionData['rule']]
}>()

// ─── Типы ───────────────────────────────────────────────────────────────────

type BlockType = 'var' | 'const' | 'operator' | 'logic' | 'not' | 'math' | 'if'

interface RuleBlock {
  id: string
  type: BlockType
  op?: string
  value?: string | number | boolean | null
  varName?: string
  children: string[]
}

// ─── Палитра ────────────────────────────────────────────────────────────────

const operatorGroups = [
  {
    label: 'Сравнение',
    color: 'amber',
    ops: [
      { op: '==', label: '== (равно)', arity: 2 },
      { op: '!=', label: '!= (не равно)', arity: 2 },
      { op: '>', label: '> (больше)', arity: 2 },
      { op: '<', label: '< (меньше)', arity: 2 },
      { op: '>=', label: '>= (больше или равно)', arity: 2 },
      { op: '<=', label: '<= (меньше или равно)', arity: 2 },
    ],
  },
  {
    label: 'Логика',
    color: 'pink',
    ops: [
      { op: 'and', label: 'AND (все условия)', arity: -1 },
      { op: 'or', label: 'OR (любое условие)', arity: -1 },
      { op: '!!', label: 'ЕСТЬ (не пусто)', arity: 1 },
      { op: '!', label: 'НЕТ (отрицание)', arity: 1 },
    ],
  },
  {
    label: 'Математика',
    color: 'teal',
    ops: [
      { op: '+', label: '+ (сложить)', arity: -1 },
      { op: '-', label: '- (вычесть)', arity: 2 },
      { op: '*', label: '* (умножить)', arity: -1 },
      { op: '/', label: '/ (разделить)', arity: 2 },
    ],
  },
  {
    label: 'Условие',
    color: 'purple',
    ops: [
      { op: 'if', label: 'IF (если…то…иначе)', arity: 3 },
    ],
  },
]

const typeColors: Record<string, string> = {
  var: 'blue', const: 'green', operator: 'amber',
  logic: 'pink', not: 'pink', math: 'teal', if: 'purple',
}

// ─── Состояние ──────────────────────────────────────────────────────────────

const blocks = ref<Map<string, RuleBlock>>(new Map())
const rootId = ref<string>('')
let nextId = 1

// ─── Парсинг JSON → блоки ───────────────────────────────────────────────────

function parseJsonLogic(obj: unknown): { root: string; all: Map<string, RuleBlock> } {
  const all = new Map<string, RuleBlock>()

  function parse(val: unknown): string {
    const id = `b-${nextId++}`

    if (val === null || val === undefined) {
      all.set(id, { id, type: 'const', value: null, children: [] })
      return id
    }
    if (typeof val === 'boolean' || typeof val === 'number' || typeof val === 'string') {
      all.set(id, { id, type: 'const', value: val, children: [] })
      return id
    }
    if (Array.isArray(val)) {
      all.set(id, { id, type: 'logic', op: 'and', children: val.map(parse) })
      return id
    }
    if (typeof val === 'object' && val !== null) {
      const entries = Object.entries(val)
      if (entries.length === 1) {
        const [op, args] = entries[0]
        if (op === 'var') {
          all.set(id, { id, type: 'var', varName: String(args), children: [] })
          return id
        }
        if (op === '!!' || op === '!') {
          all.set(id, { id, type: 'not', op, children: [parse(args)] })
          return id
        }
        if (['==', '!=', '>', '<', '>=', '<='].includes(op)) {
          const arr = Array.isArray(args) ? args : [args]
          all.set(id, { id, type: 'operator', op, children: arr.map(parse) })
          return id
        }
        if (['+', '-', '*', '/'].includes(op)) {
          const arr = Array.isArray(args) ? args : [args]
          all.set(id, { id, type: 'math', op, children: arr.map(parse) })
          return id
        }
        if (op === 'and' || op === 'or') {
          const arr = Array.isArray(args) ? args : [args]
          all.set(id, { id, type: 'logic', op, children: arr.map(parse) })
          return id
        }
        if (op === 'if') {
          const arr = Array.isArray(args) ? args : [args]
          all.set(id, { id, type: 'if', op: 'if', children: arr.map(parse) })
          return id
        }
      }
    }
    all.set(id, { id, type: 'const', value: JSON.stringify(val), children: [] })
    return id
  }

  const root = parse(obj)
  return { root, all }
}

// ─── Сборка блоков → JSON ─────────────────────────────────────────────────

function buildJsonLogic(blockId: string): unknown {
  const block = blocks.value.get(blockId)
  if (!block) return null

  switch (block.type) {
    case 'var': return { var: block.varName ?? '' }
    case 'const': return block.value ?? null
    case 'operator':
    case 'math':
    case 'logic': return { [block.op!]: block.children.map(buildJsonLogic) }
    case 'not': return { [block.op!]: buildJsonLogic(block.children[0]) }
    case 'if': return { if: block.children.map(buildJsonLogic) }
    default: return null
  }
}

// ─── Инициализация ──────────────────────────────────────────────────────────

function init() {
  nextId = 1
  const parsed = parseJsonLogic(props.modelValue)
  blocks.value = parsed.all
  rootId.value = parsed.root
}

init()

watch(() => props.modelValue, () => {
  // Проверяем, изменилось ли значение извне
  const current = rootId.value ? buildJsonLogic(rootId.value) : null
  if (JSON.stringify(current) !== JSON.stringify(props.modelValue)) {
    init()
  }
}, { deep: true })

// ─── CRUD блоков ────────────────────────────────────────────────────────────

function addBlock(type: BlockType, op?: string): string {
  const id = `b-${nextId++}`
  const block: RuleBlock = { id, type, op, children: [] }
  if (type === 'var') block.varName = ''
  if (type === 'const') block.value = ''
  blocks.value.set(id, block)
  if (!rootId.value) rootId.value = id
  emitChange()
  return id
}

function addChild(parentId: string, childId: string) {
  const parent = blocks.value.get(parentId)
  if (!parent || parent.children.includes(childId)) return
  parent.children.push(childId)
  emitChange()
}

function deleteBlock(id: string) {
  for (const [, block] of blocks.value) {
    block.children = block.children.filter((c) => c !== id)
  }
  blocks.value.delete(id)
  if (rootId.value === id) {
    const first = blocks.value.keys().next().value
    rootId.value = first ?? ''
  }
  emitChange()
}

function copyJson() {
  if (typeof navigator !== 'undefined' && navigator.clipboard) {
    void navigator.clipboard.writeText(JSON.stringify(props.modelValue, null, 2))
  }
}

function emitChange() {
  if (!rootId.value) {
    emit('update:modelValue', {})
    return
  }
  const result = buildJsonLogic(rootId.value)
  emit('update:modelValue', result as JournalConditionData['rule'])
}

// ─── Drag & Drop ────────────────────────────────────────────────────────────

const draggedOp = ref<string | null>(null)
const draggedBlockId = ref<string | null>(null)

function onDragStartOp(op: string) {
  draggedOp.value = op
}

function onDragStartBlock(blockId: string) {
  draggedBlockId.value = blockId
}

function onDropOnBlock(targetId: string, event?: DragEvent) {
  event?.preventDefault()
  event?.stopPropagation()
  if (draggedOp.value) {
    const type = draggedOp.value === 'var' ? 'var' :
                 draggedOp.value === 'const' ? 'const' :
                 draggedOp.value === 'and' || draggedOp.value === 'or' ? 'logic' :
                 draggedOp.value === '!!' || draggedOp.value === '!' ? 'not' :
                 draggedOp.value === 'if' ? 'if' :
                 ['+', '-', '*', '/'].includes(draggedOp.value) ? 'math' : 'operator'
    const newId = addBlock(type, draggedOp.value === 'var' || draggedOp.value === 'const' ? undefined : draggedOp.value)
    addChild(targetId, newId)
    draggedOp.value = null
  } else if (draggedBlockId.value && draggedBlockId.value !== targetId) {
    addChild(targetId, draggedBlockId.value)
    draggedBlockId.value = null
  }
}

function onDropOnCanvas() {
  if (draggedOp.value) {
    const type = draggedOp.value === 'var' ? 'var' :
                 draggedOp.value === 'const' ? 'const' :
                 draggedOp.value === 'and' || draggedOp.value === 'or' ? 'logic' :
                 draggedOp.value === '!!' || draggedOp.value === '!' ? 'not' :
                 draggedOp.value === 'if' ? 'if' :
                 ['+', '-', '*', '/'].includes(draggedOp.value) ? 'math' : 'operator'
    addBlock(type, draggedOp.value === 'var' || draggedOp.value === 'const' ? undefined : draggedOp.value)
    draggedOp.value = null
  }
  draggedBlockId.value = null
}

// ─── Рекурсивный компонент блока ──────────────────────────────────────────

const RuleBlockItem = defineComponent({
  name: 'RuleBlockItem',
  props: {
    blockId: { type: String, required: true },
  },
  setup(props) {
    const block = computed(() => blocks.value.get(props.blockId))
    const color = computed(() => typeColors[block.value?.type ?? 'const'])
    const isContainer = computed(() => ['operator', 'logic', 'math', 'if', 'not'].includes(block.value?.type ?? ''))

    function updateVarName(val: string) {
      if (block.value) {
        block.value.varName = val
        emitChange()
      }
    }

    function updateConstType(type: string) {
      if (!block.value) return
      block.value.value = type === 'boolean' ? false : type === 'number' ? 0 : type === 'null' ? null : ''
      emitChange()
    }

    function updateConstValue(val: string) {
      if (!block.value) return
      if (typeof block.value.value === 'boolean') {
        block.value.value = val === 'true'
      } else if (typeof block.value.value === 'number') {
        block.value.value = Number(val)
      } else {
        block.value.value = val
      }
      emitChange()
    }

    return (): VNode | null => {
      const b = block.value
      if (!b) return null

      return h('div', {
        class: ['rule-block', `rule-block--${color.value}`, { 'rule-block--container': isContainer.value }],
        draggable: true,
        onDragstart: (e: DragEvent) => { onDragStartBlock(b.id); e.stopPropagation() },
        onDragover: (e: DragEvent) => { e.preventDefault(); e.stopPropagation() },
        onDrop: (e: DragEvent) => { e.preventDefault(); e.stopPropagation(); onDropOnBlock(b.id, e) },
      }, [
        // Header
        h('div', { class: 'rule-block__header' }, [
          h('span', { class: 'rule-block__badge' }, b.op ?? b.type),
          h('button', {
            class: 'rule-block__delete',
            onClick: () => deleteBlock(b.id),
          }, '×'),
        ]),

        // Body
        h('div', { class: 'rule-block__body' }, [
          // Variable
          b.type === 'var' && h('div', { class: 'rule-block__input-row' }, [
            h('span', { class: 'rule-block__label' }, '{var}'),
            h('input', {
              class: 'rule-block__input',
              value: b.varName,
              placeholder: 'имя_поля',
              onInput: (e: Event) => updateVarName((e.target as HTMLInputElement).value),
            }),
          ]),

          // Constant
          b.type === 'const' && h('div', { class: 'rule-block__input-row' }, [
            h('select', {
              class: 'rule-block__select',
              value: b.value === null ? 'null' : typeof b.value,
              onChange: (e: Event) => updateConstType((e.target as HTMLSelectElement).value),
            }, [
              h('option', { value: 'string' }, 'Текст'),
              h('option', { value: 'number' }, 'Число'),
              h('option', { value: 'boolean' }, 'Да/Нет'),
              h('option', { value: 'null' }, 'Пусто'),
            ]),
            b.value === null
              ? h('span', { class: 'rule-block__null' }, 'null')
              : typeof b.value === 'boolean'
                ? h('input', {
                    type: 'checkbox',
                    checked: b.value,
                    onChange: (e: Event) => { b.value = (e.target as HTMLInputElement).checked; emitChange() },
                  })
                : h('input', {
                    class: 'rule-block__input',
                    type: typeof b.value === 'number' ? 'number' : 'text',
                    value: b.value ?? '',
                    onInput: (e: Event) => updateConstValue((e.target as HTMLInputElement).value),
                  }),
          ]),

          // Container children
          isContainer.value && h('div', { class: 'rule-block__children' }, [
            b.children.length === 0 && h('div', {
              class: 'rule-block__dropzone',
              onDragover: (e: DragEvent) => e.preventDefault(),
              onDrop: (e: DragEvent) => { e.preventDefault(); onDropOnBlock(b.id, e) },
            }, 'Перетащите сюда блоки'),
            ...b.children.map((childId) => h(RuleBlockItem, { key: childId, blockId: childId })),
            b.children.length > 0 && h('button', {
              class: 'rule-block__add-slot',
              onClick: () => {
                const newId = addBlock('const')
                addChild(b.id, newId)
              },
            }, '+ добавить слот'),
          ]),
        ]),
      ])
    }
  },
})
</script>

<template>
  <div class="rule-builder">
    <!-- Палитра -->
    <div class="rule-builder__palette">
      <h4 class="rule-builder__palette-title">
        Блоки
      </h4>

      <button
        class="rule-builder__palette-item rule-builder__palette-item--blue"
        draggable="true"
        @dragstart="onDragStartOp('var')"
        @click="addBlock('var')"
      >
        <span class="rule-builder__icon">{ }</span>
        Переменная
      </button>

      <button
        class="rule-builder__palette-item rule-builder__palette-item--green"
        draggable="true"
        @dragstart="onDragStartOp('const')"
        @click="addBlock('const')"
      >
        <span class="rule-builder__icon">T</span>
        Константа
      </button>

      <div v-for="group in operatorGroups" :key="group.label" class="rule-builder__group">
        <span class="rule-builder__group-label">{{ group.label }}</span>
        <button
          v-for="op in group.ops"
          :key="op.op"
          class="rule-builder__palette-item"
          :class="`rule-builder__palette-item--${group.color}`"
          draggable="true"
          @dragstart="onDragStartOp(op.op)"
          @click="addBlock(
            op.op === 'and' || op.op === 'or' ? 'logic' :
            op.op === '!!' || op.op === '!' ? 'not' :
            op.op === 'if' ? 'if' :
            ['+', '-', '*', '/'].includes(op.op) ? 'math' : 'operator',
            op.op
          )"
        >
          {{ op.label }}
        </button>
      </div>
    </div>

    <!-- Канвас -->
    <div
      class="rule-builder__canvas"
      @dragover.prevent
      @drop.prevent="onDropOnCanvas"
    >
      <div v-if="!rootId" class="rule-builder__empty">
        <span class="text-2xl mb-2">🧩</span>
        <p class="text-sm text-muted">
          Нажмите блок из палитры или перетащите сюда
        </p>
      </div>

      <RuleBlockItem v-else :block-id="rootId" />

      <!-- Предпросмотр JSON -->
      <div class="rule-builder__preview">
        <div class="rule-builder__preview-header">
          <span class="text-xs font-medium text-muted">JSON</span>
          <button class="rule-builder__copy-btn" @click="copyJson">
            📋 Копировать
          </button>
        </div>
        <pre class="rule-builder__preview-code">{{ JSON.stringify(modelValue, null, 2) }}</pre>
      </div>
    </div>
  </div>
</template>

<style scoped>
.rule-builder {
  display: grid;
  grid-template-columns: 160px 1fr;
  gap: 10px;
  min-height: 360px;
}
.rule-builder__palette {
  background: var(--ui-bg-muted);
  border-radius: 10px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow-y: auto;
  max-height: 480px;
}
.rule-builder__palette-title {
  font-size: 11px;
  font-weight: 700;
  color: var(--ui-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 2px;
}
.rule-builder__group {
  display: flex;
  flex-direction: column;
  gap: 3px;
  margin-top: 4px;
}
.rule-builder__group-label {
  font-size: 9px;
  color: var(--ui-text-muted);
  font-weight: 600;
  text-transform: uppercase;
}
.rule-builder__palette-item {
  --rb: var(--ui-primary);
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 7px;
  border-radius: 6px;
  border: 1px solid color-mix(in oklab, var(--rb) 45%, var(--ui-border));
  color: var(--rb);
  background: var(--ui-bg);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.15s;
  text-align: left;
  line-height: 1.3;
}
.rule-builder__palette-item:hover {
  transform: translateY(-1px);
  background: color-mix(in oklab, var(--rb) 12%, transparent);
  box-shadow: 0 2px 4px rgb(0 0 0 / 0.08);
}
.rule-builder__icon {
  font-size: 10px;
  font-weight: 700;
  font-family: ui-monospace, monospace;
  opacity: 0.7;
}
/* Акцент типа блока — семантические токены Nuxt UI (адаптируются к теме). */
.rule-builder__palette-item--blue { --rb: var(--ui-info); }
.rule-builder__palette-item--green { --rb: var(--ui-success); }
.rule-builder__palette-item--amber { --rb: var(--ui-warning); }
.rule-builder__palette-item--pink { --rb: var(--ui-error); }
.rule-builder__palette-item--teal { --rb: var(--ui-primary); }
.rule-builder__palette-item--purple { --rb: var(--ui-secondary); }

.rule-builder__canvas {
  background: var(--ui-bg);
  border: 1px dashed var(--ui-border);
  border-radius: 10px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
  min-height: 300px;
}
.rule-builder__empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 160px;
  color: var(--ui-text-muted);
}

/* ─── Блоки ──────────────────────────────────────────────────────────────── */

.rule-block {
  border-radius: 8px;
  border: 1.5px solid;
  background: var(--ui-bg);
  overflow: hidden;
  margin-bottom: 6px;
  transition: box-shadow 0.15s;
}
.rule-block:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.rule-block--blue { border-color: color-mix(in oklab, var(--ui-info) 55%, var(--ui-border)); }
.rule-block--green { border-color: color-mix(in oklab, var(--ui-success) 55%, var(--ui-border)); }
.rule-block--amber { border-color: color-mix(in oklab, var(--ui-warning) 55%, var(--ui-border)); }
.rule-block--pink { border-color: color-mix(in oklab, var(--ui-error) 55%, var(--ui-border)); }
.rule-block--teal { border-color: color-mix(in oklab, var(--ui-primary) 55%, var(--ui-border)); }
.rule-block--purple { border-color: color-mix(in oklab, var(--ui-secondary) 55%, var(--ui-border)); }

.rule-block--container {
  background: var(--ui-bg-muted);
}

.rule-block__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 5px 9px;
  background: var(--ui-bg-elevated);
  border-bottom: 1px solid var(--ui-border);
}
.rule-block__badge {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: 4px;
  background: var(--ui-bg);
  color: var(--ui-text);
  font-family: ui-monospace, monospace;
}
.rule-block__delete {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  font-size: 14px;
  color: var(--ui-text-muted);
  cursor: pointer;
  border: none;
  background: transparent;
  line-height: 1;
}
.rule-block__delete:hover {
  background: var(--ui-error);
  color: white;
}

.rule-block__body {
  padding: 8px;
}
.rule-block__input-row {
  display: flex;
  align-items: center;
  gap: 6px;
}
.rule-block__label {
  font-size: 10px;
  color: var(--ui-text-muted);
  font-weight: 600;
  white-space: nowrap;
  font-family: ui-monospace, monospace;
}
.rule-block__input {
  flex: 1;
  padding: 3px 7px;
  border-radius: 5px;
  border: 1px solid var(--ui-border);
  background: var(--ui-bg);
  font-size: 11px;
  min-width: 0;
}
.rule-block__input:focus {
  outline: none;
  border-color: var(--ui-primary);
}
.rule-block__select {
  padding: 3px 6px;
  border-radius: 5px;
  border: 1px solid var(--ui-border);
  background: var(--ui-bg);
  font-size: 11px;
}
.rule-block__null {
  font-size: 10px;
  color: var(--ui-text-muted);
  font-style: italic;
}

.rule-block__children {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-left: 12px;
  border-left: 2px solid var(--ui-border);
  margin-left: 3px;
}
.rule-block__dropzone {
  padding: 12px;
  border: 2px dashed var(--ui-border);
  border-radius: 6px;
  text-align: center;
  font-size: 11px;
  color: var(--ui-text-muted);
  background: var(--ui-bg);
}
.rule-block__add-slot {
  padding: 3px 8px;
  border-radius: 5px;
  border: 1px dashed var(--ui-border);
  background: transparent;
  font-size: 10px;
  color: var(--ui-text-muted);
  cursor: pointer;
  align-self: flex-start;
}
.rule-block__add-slot:hover {
  border-color: var(--ui-primary);
  color: var(--ui-primary);
}

/* ─── Предпросмотр ─────────────────────────────────────────────────────── */

.rule-builder__preview {
  margin-top: auto;
  border-radius: 8px;
  border: 1px solid var(--ui-border);
  overflow: hidden;
}
.rule-builder__preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 5px 9px;
  background: var(--ui-bg-muted);
  border-bottom: 1px solid var(--ui-border);
}
.rule-builder__copy-btn {
  font-size: 10px;
  color: var(--ui-primary);
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
}
.rule-builder__copy-btn:hover {
  background: var(--ui-bg-elevated);
}
.rule-builder__preview-code {
  padding: 8px;
  font-size: 10px;
  font-family: ui-monospace, monospace;
  background: var(--ui-bg-elevated);
  color: var(--ui-text);
  overflow-x: auto;
  white-space: pre-wrap;
  max-height: 100px;
  overflow-y: auto;
  margin: 0;
}
</style>