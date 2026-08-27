<script setup lang="ts">
// components/WorkflowPreview.vue
// Preview-песочница прохождения процесса на ЧЕРНОВОЙ (в т.ч. несохранённой) схеме
// (US-008). Чтение реальное (движок + рендерер + SDK справочников), запись НЕ
// выполняется: движок создаётся без onSave (persist — no-op), а доменные действия
// шага НЕ уходят в execute-step — вместо этого перехватываются в previewLog
// («что было бы вызвано»). Ноль createEntry/saveEntryProgress/executeStep за сессию.
//
// RouteTrace: read-only VueFlow тех же нод/рёбер с подсветкой пройденного маршрута
// (engine.history + текущий шаг) — переиспользует те же компоненты нод, что билдер.

import { computed, markRaw, ref, watch } from 'vue'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { VueFlow, type NodeTypesObject } from '@vue-flow/core'
import WorkflowScreenRenderer from '@/modules/workflows/components/WorkflowScreenRenderer.vue'
import { useJournalEngine } from '@/modules/workflows/composables/useJournalEngine'
import { ensureV2 } from '@/modules/workflows/engine/convert'
import { buildPreviewActionEntry, type PreviewActionEntry } from '@/modules/workflows/engine/preview'
import type { JournalEdge, JournalNode, JournalSchema, JournalStepData } from '@/modules/workflows/types/journal'
import JournalConditionNode from './nodes/JournalConditionNode.vue'
import JournalEndNode from './nodes/JournalEndNode.vue'
import JournalLoopNode from './nodes/JournalLoopNode.vue'
import JournalStartNode from './nodes/JournalStartNode.vue'
import JournalStepNode from './nodes/JournalStepNode.vue'

const props = defineProps<{
  // Черновая схема из билдера (редактируемое состояние). Preview работает даже на
  // несохранённой версии — движок читает её напрямую.
  schema: JournalSchema
}>()


// Движок БЕЗ onSave и БЕЗ initialEntry → чистый прогон in-memory, нулевая
// персистентность: reset()/goNext()/addLoopItem() вызывают внутренний persist(),
// который без onSave ничего не делает.
const engine = useJournalEngine(props.schema)

const stepData = computed(() => engine.currentStep.value.data as JournalStepData)

// ─── Журнал перехваченных доменных действий («что было бы отправлено») ─────────

type LoggedEntry = PreviewActionEntry & { index: number }
const previewLog = ref<LoggedEntry[]>([])
const totalCalls = computed(() => previewLog.value.reduce((sum, e) => sum + e.calls.length, 0))

// Обёртка «Далее»: доменные действия шага НЕ исполняются на сервере — вместо
// execute-step собираем запись перехвата и кладём в лог, затем обычный переход.
function onNext() {
  if (!engine.canGoNext.value || engine.isFinished.value) return
  const step = engine.currentStep.value
  const entry = buildPreviewActionEntry(step, {
    answers: engine.answers.value,
    actorId: null,
    // Actor identity is resolved by the backend. Область
    // (scope) в песочнице не задана — scope-цели резолвятся уже в раннере.
    scopeId: undefined,
  })
  if (entry) {
    previewLog.value.push({ ...entry, index: previewLog.value.length + 1 })
  }
  engine.goNext()
}

function resetPreview() {
  engine.reset()
  previewLog.value = []
}

// Краткая сводка одной итерации цикла (как в раннере) для списка добавленных.
function loopItemSummary(item: Record<string, unknown>): string {
  return engine.currentFields.value
    .map((f) => {
      const v = item[f.id]
      if (v === undefined || v === null || v === '') return null
      if (f.type === 'boolean') return `${f.label}: ${v ? 'да' : 'нет'}`
      if (f.type === 'select') {
        const opt = f.options?.find((o) => o.value === v)
        return `${f.label}: ${opt?.label ?? v}`
      }
      return `${f.label}: ${v}`
    })
    .filter(Boolean)
    .join(' · ')
}

function formatArgs(args: Record<string, unknown>): string {
  const keys = Object.keys(args)
  if (!keys.length) return '—'
  return keys.map((k) => `${k}: ${JSON.stringify(args[k])}`).join(', ')
}

// ─── RouteTrace: read-only граф с подсветкой маршрута ─────────────────────────

const nodeTypes = {
  start: markRaw(JournalStartNode),
  step: markRaw(JournalStepNode),
  condition: markRaw(JournalConditionNode),
  loop: markRaw(JournalLoopNode),
  end: markRaw(JournalEndNode),
} as unknown as NodeTypesObject

// Нормализованная схема (v2) — те же позиции/данные, что видит билдер.
const base = computed(() => ensureV2(props.schema))
const startId = computed(() => base.value.nodes.find((n) => n.type === 'start')?.id ?? null)
const flowId = computed(() => `wf-preview-${props.schema.id}`)

// Класс подсветки узла: текущий шаг — акцент; пройденный (история + старт) —
// мягкий акцент; непройденный — приглушён (см. стиль ниже).
function traceClass(id: string, visited: Set<string>, current: string): string {
  const isCurrent = id === current
  const isVisited = visited.has(id) || id === startId.value
  return [isVisited && !isCurrent ? 'wf-trace--visited' : '', isCurrent ? 'wf-trace--current' : '']
    .filter(Boolean)
    .join(' ')
}

// Ребро «пройдено», если и источник, и цель уже посещены (или цель — текущий
// шаг) — у непройденной ветки условия (например «Нет», когда пошли по «Да»)
// цель в visited не попадёт, и ребро останется в состоянии «впереди».
function traceEdgeClass(source: string, target: string, visited: Set<string>, current: string): string {
  const sourceOk = visited.has(source) || source === startId.value
  const targetOk = visited.has(target) || target === current
  if (!sourceOk || !targetOk) return ''
  return target === current ? 'wf-trace-edge--current' : 'wf-trace-edge--visited'
}

// v-model:nodes для VueFlow. Переприсваиваем массив при навигации, чтобы граф
// пересинхронизировал классы подсветки. Read-only: перетаскивание/выделение off.
// Типы — обёртки над JournalNode/JournalEdge (без domAttributes VueFlow), как в
// билдере: так VueFlow-проп принимает их без конфликта глубоких типов.
type TraceNode = JournalNode & { class?: string, draggable?: boolean, selectable?: boolean }
type TraceEdge = JournalEdge & { selectable?: boolean, class?: string, animated?: boolean }

const graphNodes = ref<TraceNode[]>([])
const graphEdges = ref<TraceEdge[]>([])

function rebuildGraph() {
  const visited = new Set(engine.history.value)
  const current = engine.currentStep.value.id
  graphNodes.value = base.value.nodes.map((n) => ({
    ...n,
    draggable: false,
    selectable: false,
    class: traceClass(n.id, visited, current),
  }))
  graphEdges.value = base.value.edges.map((e) => {
    const cls = traceEdgeClass(e.source, e.target, visited, current)
    // e.class уже может нести цвет ветки условия (wf-edge--true/false из
    // JournalBuilder) — сохраняем его вместе с классом трассировки маршрута.
    return { ...e, selectable: false, class: [e.class, cls].filter(Boolean).join(' '), animated: cls === 'wf-trace-edge--current' }
  })
}

watch(
  [() => engine.history.value.slice(), () => engine.currentStep.value.id, base],
  rebuildGraph,
  { immediate: true, deep: true },
)
</script>

<template>
  <div class="flex flex-col gap-4">
    <!-- Плашка режима -->
    <UAlert
      color="info"
      variant="subtle"
      icon="i-lucide-flask-conical"
      title="Режим предпросмотра"
      description="Прохождение черновой схемы без сохранения. Чтение справочников — реальное; доменные действия и запись прогресса перехватываются в журнал ниже и НЕ отправляются на сервер."
    />

    <div class="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <!-- Основная колонка: экран шага + навигация -->
      <UCard>
        <template #header>
          <div class="flex items-center justify-between gap-2">
            <div class="min-w-0">
              <h2 class="font-semibold truncate">
                {{ schema.title }}
              </h2>
              <div class="text-xs text-muted mt-0.5">
                Черновая схема · предпросмотр
              </div>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <UBadge v-if="!engine.isFinished.value" color="neutral" variant="subtle">
                Шаг {{ engine.history.value.length + 1 }}
              </UBadge>
              <UButton
                size="xs"
                variant="ghost"
                color="neutral"
                icon="i-lucide-rotate-ccw"
                @click="resetPreview"
              >
                Сброс
              </UButton>
            </div>
          </div>
          <div v-if="!engine.isFinished.value" class="mt-3">
            <UProgress :model-value="engine.progress.value" size="sm" />
            <p class="mt-1 text-xs text-muted">
              {{ engine.progress.value }}% пройдено
            </p>
          </div>
        </template>

        <template v-if="!engine.isFinished.value">
          <h3 class="text-base font-medium mb-1">
            {{ stepData.label }}
          </h3>
          <p v-if="stepData.description" class="text-sm text-muted mb-4">
            {{ stepData.description }}
          </p>

          <!-- Рендер экрана. run-id НЕ передаём → загрузка файлов деактивирована;
             чтение справочников (dictionary) остаётся реальным. -->
          <WorkflowScreenRenderer
            v-model="engine.answers.value"
            :screen="engine.currentScreen.value"
          />

          <!-- Циклическая нода: добавление/удаление итераций (как в раннере) -->
          <div
            v-if="engine.currentLoop.value"
            class="mt-5 rounded-lg border border-dashed border-success/40 bg-success/5 p-3.5"
          >
            <div class="mb-2.5 flex items-center gap-1.5 text-xs font-semibold text-muted">
              <UIcon name="i-lucide-repeat" class="size-4 text-success" />
              <span>Добавлено: {{ engine.loopItems.value.length }}</span>
            </div>

            <div v-if="engine.loopItems.value.length" class="flex flex-col gap-1.5">
              <div
                v-for="(item, i) in engine.loopItems.value"
                :key="i"
                class="flex items-center gap-2 rounded-md border border-default bg-default px-2 py-1.5"
              >
                <UBadge
                  :label="String(i + 1)"
                  color="success"
                  variant="soft"
                  size="sm"
                />
                <span class="min-w-0 flex-1 truncate text-xs">{{ loopItemSummary(item) }}</span>
                <UButton
                  size="xs"
                  color="error"
                  variant="ghost"
                  icon="i-lucide-x"
                  @click="engine.removeLoopItem(i)"
                />
              </div>
            </div>
            <p v-else class="text-xs text-muted">
              Пока ничего не добавлено. Добавьте сколько нужно или сразу нажмите «Далее».
            </p>

            <UButton
              class="mt-3"
              variant="soft"
              color="success"
              icon="i-lucide-plus"
              :label="`Добавить ${engine.currentLoop.value.itemNoun || 'запись'}`"
              :disabled="!engine.canAddLoopItem.value"
              @click="engine.addLoopItem()"
            />
          </div>
        </template>

        <template v-else>
          <div class="py-8 text-center">
            <UIcon name="i-lucide-flag" class="mx-auto size-10 text-success" />
            <p class="mt-2 font-medium">
              Прохождение завершено
            </p>
            <p class="text-sm text-muted">
              Это предпросмотр — ничего не сохранено. Нажмите «Сброс», чтобы пройти заново.
            </p>
          </div>
        </template>

        <template #footer>
          <div class="flex items-center justify-between">
            <UButton
              variant="ghost"
              color="neutral"
              :disabled="!engine.history.value.length"
              @click="engine.goBack"
            >
              Назад
            </UButton>
            <UButton
              v-if="!engine.isFinished.value"
              :disabled="!engine.canGoNext.value"
              :icon="engine.currentLoop.value ? 'i-lucide-log-out' : undefined"
              @click="onNext"
            >
              {{ engine.currentLoop.value ? 'Завершить и далее' : 'Далее' }}
            </UButton>
            <UButton
              v-else
              variant="soft"
              color="neutral"
              icon="i-lucide-rotate-ccw"
              @click="resetPreview"
            >
              Пройти заново
            </UButton>
          </div>
        </template>
      </UCard>

      <!-- Боковая колонка: RouteTrace + журнал перехвата -->
      <aside class="flex flex-col gap-4">
        <!-- RouteTrace: read-only граф с подсветкой маршрута -->
        <UCard :ui="{ body: 'p-0 sm:p-0' }">
          <template #header>
            <div class="flex items-center gap-1.5 text-sm font-semibold text-highlighted">
              <UIcon name="i-lucide-route" class="size-4" />
              <span>Маршрут</span>
            </div>
          </template>
          <div class="wf-preview__trace">
            <VueFlow
              :id="flowId"
              v-model:nodes="graphNodes"
              v-model:edges="graphEdges"
              :node-types="nodeTypes"
              :default-edge-options="{ type: 'smoothstep' }"
              :nodes-draggable="false"
              :nodes-connectable="false"
              :elements-selectable="false"
              :min-zoom="0.1"
              fit-view-on-init
              :fit-view-options="{ padding: 0.18 }"
            >
              <Background pattern-color="#aaa" :gap="16" />
              <Controls :show-interactive="false" />
            </VueFlow>
          </div>
        </UCard>

        <!-- Журнал перехваченных доменных вызовов -->
        <UCard :ui="{ body: 'p-4 sm:p-4' }">
          <template #header>
            <div class="flex items-center justify-between gap-2">
              <div class="flex items-center gap-1.5 text-sm font-semibold text-highlighted">
                <UIcon name="i-lucide-list-plus" class="size-4" />
                <span>Что было бы вызвано</span>
              </div>
              <UBadge
                :label="String(totalCalls)"
                :color="totalCalls ? 'primary' : 'neutral'"
                variant="subtle"
                size="sm"
              />
            </div>
          </template>

          <div v-if="previewLog.length" class="flex flex-col gap-2.5">
            <div
              v-for="entry in previewLog"
              :key="`${entry.index}-${entry.nodeId}`"
              class="rounded-lg border border-default bg-elevated/40 p-2.5"
            >
              <div class="mb-1.5 flex items-center gap-1.5">
                <UBadge
                  :label="String(entry.index)"
                  size="xs"
                  variant="soft"
                  color="neutral"
                />
                <span class="min-w-0 truncate text-xs font-semibold text-highlighted">
                  {{ entry.nodeLabel }}
                </span>
              </div>
              <div class="flex flex-col gap-1.5">
                <div
                  v-for="call in entry.calls"
                  :key="call.actionId"
                  class="rounded-md border border-default bg-default px-2 py-1.5"
                >
                  <div class="flex items-center gap-1.5">
                    <UIcon name="i-lucide-zap" class="size-3.5 text-primary" />
                    <span class="text-xs font-medium text-highlighted">{{ call.label }}</span>
                    <UBadge
                      :label="call.command"
                      size="xs"
                      variant="subtle"
                      color="neutral"
                    />
                  </div>
                  <p class="mt-1 break-words font-mono text-[10.5px] leading-relaxed text-muted">
                    {{ formatArgs(call.resolvedArgs) }}
                  </p>
                </div>
              </div>
            </div>
          </div>
          <p v-else class="text-xs text-muted">
            Пока ничего не перехвачено. Пройдите шаги с доменными действиями — их вызовы появятся здесь
            вместо отправки на сервер.
          </p>
        </UCard>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.wf-preview__trace {
  height: 340px;
  width: 100%;
  border-bottom-left-radius: var(--ui-radius, 8px);
  border-bottom-right-radius: var(--ui-radius, 8px);
  overflow: hidden;
  background: var(--ui-bg-muted);
}

/* Подсветка маршрута на нодах графа. Классы навешиваются на .vue-flow__node из
   graphNodes[].class; :deep нужен, чтобы достать вложенный .wf-node. */
:deep(.vue-flow__node.wf-trace--visited .wf-node) {
  border-color: color-mix(in oklab, var(--ui-primary) 55%, var(--ui-border));
  box-shadow: 0 0 0 2px color-mix(in oklab, var(--ui-primary) 20%, transparent);
}
:deep(.vue-flow__node.wf-trace--current .wf-node) {
  border-color: var(--ui-primary);
  box-shadow: 0 0 0 3px color-mix(in oklab, var(--ui-primary) 38%, transparent);
}
:deep(.vue-flow__node:not(.wf-trace--visited):not(.wf-trace--current) .wf-node) {
  opacity: 0.5;
}

/* Подсветка маршрута на рёбрах: пройденные — сплошные и чёткие, ребро к
   текущему шагу — акцентное и «бегущее» (animated из graphEdges[].animated),
   непройденные — приглушены (item 3/4 фидбека по дизайну канваса). */
:deep(.vue-flow__edge.wf-trace-edge--visited .vue-flow__edge-path) {
  stroke: var(--ui-primary);
  opacity: 0.7;
}
:deep(.vue-flow__edge.wf-trace-edge--current .vue-flow__edge-path) {
  stroke: var(--ui-primary);
  stroke-width: 2.5;
}
:deep(.vue-flow__edge:not(.wf-trace-edge--visited):not(.wf-trace-edge--current) .vue-flow__edge-path) {
  opacity: 0.35;
}
</style>
