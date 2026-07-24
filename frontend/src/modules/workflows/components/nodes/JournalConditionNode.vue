<script setup lang="ts">
// components/nodes/JournalConditionNode.vue
import { computed } from 'vue';
import { Handle, Position } from '@vue-flow/core';
import type { JournalConditionData } from '@/modules/workflows/types/journal';

const props = defineProps<{
  data: JournalConditionData
  selected?: boolean
}>()

/**
 * Преобразуем json-logic rule в читаемую строку на русском
 */
const readableRule = computed(() => {
  const r = props.data.rule
  if (!r || typeof r !== 'object') return '—'

  const ops: Record<string, string> = {
    '==': '=', '!=': '≠', '>': '>', '<': '<',
    '>=': '≥', '<=': '≤', '!!': 'заполнено', '!': 'не',
    'and': 'И', 'or': 'ИЛИ', '+': '+', '-': '-', '*': '×', '/': '÷',
  }

  function format(val: unknown): string {
    if (val === null || val === undefined) return 'пусто'
    if (val === true) return 'да'
    if (val === false) return 'нет'
    if (typeof val === 'number') return String(val)
    if (typeof val === 'string') return `"${val}"`
    if (Array.isArray(val)) return val.map(format).join(', ')
    if (typeof val === 'object') {
      const entries = Object.entries(val)
      if (entries.length === 1) {
        const [op, args] = entries[0]
        if (op === 'var') return `{${args}}`
        const symbol = ops[op] ?? op
        if (Array.isArray(args)) {
          if (args.length === 1 && (op === '!!' || op === '!')) return `${symbol} ${format(args[0])}`
          if (op === 'if') {
            const [cond, then_, else_] = args
            return `если ${format(cond)} то ${format(then_)} иначе ${format(else_ ?? null)}`
          }
          return args.map(format).join(` ${symbol} `)
        }
        return `${symbol} ${format(args)}`
      }
      return JSON.stringify(val)
    }
    return String(val)
  }

  return format(r)
})

/**
 * Извлекаем переменные (поля), которые использует правило
 */
const usedVars = computed(() => {
  const vars: string[] = []
  function scan(val: unknown) {
    if (Array.isArray(val)) val.forEach(scan)
    else if (val && typeof val === 'object') {
      Object.entries(val).forEach(([k, v]) => {
        if (k === 'var' && typeof v === 'string') vars.push(v)
        else scan(v)
      })
    }
  }
  scan(props.data.rule)
  return [...new Set(vars)]
})
</script>

<template>
  <div class="wf-node wf-node--condition" :class="{ 'wf-node--selected': selected }">
    <Handle type="target" :position="Position.Top" />

    <div class="wf-node__header">
      <span class="wf-node__icon">
        <UIcon name="i-lucide-git-branch" class="size-4" />
      </span>
      <div class="wf-node__heading">
        <span class="wf-node__kicker">Условие</span>
        <span class="wf-node__title">{{ data.label }}</span>
      </div>
    </div>

    <div class="wf-node__body">
      <!-- Читаемое правило -->
      <div class="wf-cond__rule">
        {{ readableRule }}
      </div>

      <!-- Переменные -->
      <div v-if="usedVars.length" class="wf-cond__vars">
        <span v-for="v in usedVars" :key="v" class="wf-cond__var">{{ v }}</span>
      </div>

      <!-- Ветки (выровнены по хэндлам на нижней грани: true слева, false справа) -->
      <div class="wf-cond__branches">
        <span class="wf-cond__branch wf-cond__branch--true">
          <UIcon name="i-lucide-check" class="size-3" /> Да
        </span>
        <span class="wf-cond__branch wf-cond__branch--false">
          <UIcon name="i-lucide-x" class="size-3" /> Нет
        </span>
      </div>
    </div>

    <!-- id хэндла должен совпадать с edge.sourceHandle в схеме ('true' / 'false') -->
    <Handle
      id="true"
      type="source"
      :position="Position.Bottom"
      class="wf-handle--true"
    />
    <Handle
      id="false"
      type="source"
      :position="Position.Bottom"
      class="wf-handle--false"
    />
  </div>
</template>

<style scoped>
.wf-cond__rule {
  padding: 8px 10px;
  font-size: 12.5px;
  font-weight: 500;
  line-height: 1.45;
  color: var(--ui-text-highlighted);
  background: var(--ui-bg-muted);
  border-radius: var(--ui-radius);
  border-left: 3px solid var(--ui-warning);
  word-break: break-word;
}
.wf-cond__vars {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.wf-cond__var {
  font-size: 10px;
  font-weight: 500;
  padding: 2px 7px;
  border-radius: var(--ui-radius);
  color: var(--ui-primary);
  background: color-mix(in oklab, var(--ui-primary) 12%, transparent);
}
.wf-cond__branches {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  gap: 6px;
  margin-top: 2px;
}
.wf-cond__branch {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 10px;
  font-weight: 600;
  padding: 2px 9px;
  border-radius: 999px;
}
.wf-cond__branch--true {
  color: var(--ui-success);
  background: color-mix(in oklab, var(--ui-success) 14%, transparent);
}
.wf-cond__branch--false {
  color: var(--ui-error);
  background: color-mix(in oklab, var(--ui-error) 14%, transparent);
}

/* Хэндлы веток на нижней грани, side-by-side: true слева, false справа */
:deep(.wf-handle--true) {
  left: 32% !important;
  bottom: -6px !important;
  top: auto !important;
  background: var(--ui-success) !important;
  border-color: var(--ui-success) !important;
}
:deep(.wf-handle--false) {
  left: 68% !important;
  bottom: -6px !important;
  top: auto !important;
  background: var(--ui-error) !important;
  border-color: var(--ui-error) !important;
}
</style>
