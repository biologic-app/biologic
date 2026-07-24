<script setup lang="ts">
// components/nodes/JournalConditionNode.vue
import { useWorkflowNodeDimmed } from '@/modules/workflows/composables/useWorkflowHighlight';
import { useWorkflowNodeMenu } from '@/modules/workflows/composables/useWorkflowNodeMenu';
import type { JournalConditionData } from '@/modules/workflows/types/journal';
import { Handle, Position } from '@vue-flow/core';
import { computed } from 'vue';

const props = defineProps<{
  id: string
  data: JournalConditionData
  selected?: boolean
}>()

const dimmed = useWorkflowNodeDimmed(computed(() => props.id))
const openNodeMenu = useWorkflowNodeMenu()

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
  <div
    class="wf-node wf-node--condition"
    :class="{ 'wf-node--selected': selected, 'wf-node--dimmed': dimmed }"
  >
    <Handle type="target" :position="Position.Top" />

    <div class="wf-node__header">
      <div class="wf-node__header-row">
        <span class="wf-node__icon">
          <UIcon name="i-lucide-split" class="size-4" />
        </span>
        <div class="wf-node__heading">
          <span class="wf-node__title">{{ data.label }}</span>
        </div>
        <button type="button" class="wf-node__menu" @click.stop="openNodeMenu(id, $event)">
          <UIcon name="i-lucide-grip-vertical" class="size-3.5" />
        </button>
      </div>
      <p v-if="data.description" class="wf-node__desc">
        {{ data.description }}
      </p>
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
    </div>

    <!-- Ветки — подписи «Да»/«Нет» теперь на самих рёбрах (edge.label), а не
         кнопками внутри карточки; здесь остаются только цветовые маркеры
         хэндлов ниже, выровненные под ними (true слева, false справа). -->

    <!-- id хэндла должен совпадать с edge.sourceHandle в схеме ('true' / 'false') -->
    <Handle
      id="true"
      type="source"
      :position="Position.Right"
      class="wf-handle--true"
    />
    <Handle
      id="false"
      type="source"
      :position="Position.Left"
      class="wf-handle--false"
    />
  </div>
</template>

<style scoped>
.wf-cond__rule {
  padding: 6px 9px;
  font-size: 12px;
  font-weight: 500;
  line-height: 1.45;
  color: var(--ui-text-highlighted);
  background: var(--ui-bg-muted);
  border-radius: var(--ui-radius);
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
  color: var(--ui-text-muted);
  background: var(--ui-bg-muted);
  border: 1px solid var(--ui-border);
}
/* Хэндлы веток на нижней грани, side-by-side: «Да» справа, «Нет» слева.
   bottom: 0 (не -6px) — так же, как у стандартного .vue-flow__handle-bottom,
   кружок ровно straddle-ит границу карточки, а не висит ниже неё. */
:deep(.wf-handle--true) {
  background: var(--ui-bg) !important;
  border-color: var(--ui-success) !important;
}
:deep(.wf-handle--false) {
  background: var(--ui-bg) !important;
  border-color: var(--ui-error) !important;
}
</style>
