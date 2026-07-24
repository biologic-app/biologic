<script setup lang="ts">
// components/JournalBuilder.vue
// Конструктор с графическим редактором правил

import {
  exportTemplate,
  getSchemaVersions,
  getTemplate,
  importData,
  saveSchemaVersion,
  updateCurrentSchema,
} from '@/modules/workflows/api/workflows.api'
import { provideWorkflowHighlight } from '@/modules/workflows/composables/useWorkflowHighlight'
import { useWorkflowLayout } from '@/modules/workflows/composables/useWorkflowLayout'
import { provideWorkflowNodeMenu } from '@/modules/workflows/composables/useWorkflowNodeMenu'
import { ensureV2, screenFields, toScreen } from '@/modules/workflows/engine/convert'
import type { DomainAction, JournalConditionData, JournalEdge, JournalLoopData, JournalNode, JournalSchema, JournalStepData, Screen } from '@/modules/workflows/types/journal'
import RowContextMenu from '@/shared/ui/RowContextMenu.vue'
import type { DropdownMenuItem } from '@nuxt/ui'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { VueFlow, useNodesInitialized, useVueFlow, type Connection, type NodeMouseEvent, type NodeTypesObject } from '@vue-flow/core'
import { MiniMap } from '@vue-flow/minimap'
import { computed, markRaw, nextTick, onMounted, ref, watch } from 'vue'
import JournalConditionNode from './nodes/JournalConditionNode.vue'
import JournalEndNode from './nodes/JournalEndNode.vue'
import JournalLoopNode from './nodes/JournalLoopNode.vue'
import JournalStartNode from './nodes/JournalStartNode.vue'
import JournalStepNode from './nodes/JournalStepNode.vue'
import WorkflowNodeSlideover from './WorkflowNodeSlideover.vue'

// Подпись + цвет ветки условия — на самом ребре (item 2 фидбека), не кнопкой
// внутри карточки; id хэндла остаётся 'true'/'false' (движок/раннер резолвят
// по нему). Цвет ребра совпадает с цветом хэндла: «Да» — зелёный, «Нет» — красный.
function branchLabel(sourceHandle: string | null | undefined): string | undefined {
  if (sourceHandle === 'true') return 'Да'
  if (sourceHandle === 'false') return 'Нет'
  return undefined
}
function branchClass(sourceHandle: string | null | undefined): string | undefined {
  if (sourceHandle === 'true') return 'wf-edge--true'
  if (sourceHandle === 'false') return 'wf-edge--false'
  return undefined
}
function withBranchLabels(list: JournalEdge[]): JournalEdge[] {
  return list.map((edge) => ({
    ...edge,
    label: branchLabel(edge.sourceHandle) ?? edge.label,
    class: branchClass(edge.sourceHandle),
  }))
}

// Таскать карточку можно только за «⋯» в шапке — не за произвольное место
// (клики по полям/кнопкам внутри тела ноды не должны задевать drag).
const DRAG_HANDLE_SELECTOR = '.wf-node__menu'
function withDragHandle(list: JournalNode[]): JournalNode[] {
  return list.map((node) => ({ ...node, dragHandle: DRAG_HANDLE_SELECTOR }))
}

const props = defineProps<{
  modelValue: JournalSchema
  templateId: string
}>()
const emit = defineEmits<{
  'update:modelValue': [JournalSchema]
  'version-saved': [number]
}>()

const toast = useToast()

const nodeTypes = {
  start: markRaw(JournalStartNode),
  step: markRaw(JournalStepNode),
  condition: markRaw(JournalConditionNode),
  loop: markRaw(JournalLoopNode),
  end: markRaw(JournalEndNode),
} as unknown as NodeTypesObject

const { onConnect, addEdges, removeNodes, fitView } = useVueFlow()
const { layout } = useWorkflowLayout()

// Глубокая копия схемы под редактирование. structuredClone падает на реактивных
// прокси Vue (DataCloneError), поэтому клонируем через JSON — схема сериализуема,
// а результат заодно теряет реактивность (билдеру нужна своя мутируемая копия).
const cloneData = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T

// Нормализуем к v2 при загрузке: у каждого step/loop-узла появляется data.screen,
// который редактирует ScreenEditor (US-006). Плоский fields[] остаётся как есть —
// раннер через toScreen предпочитает screen, поэтому источник истины экрана один.
const nodes = ref<JournalNode[]>(withDragHandle(cloneData(ensureV2(props.modelValue).nodes)))
const edges = ref<JournalEdge[]>(withBranchLabels(cloneData(props.modelValue.edges)))
const selectedNodeId = ref<string | null>(null)
const showVersionModal = ref(false)
const versionNote = ref('')
const importInput = ref<HTMLInputElement | null>(null)
const canvasEl = ref<HTMLElement | null>(null)

const selectedNode = computed(() => nodes.value.find((n) => n.id === selectedNodeId.value) ?? null)
const slideoverOpen = ref(false)

// Загрузка версий (из API). Обновляется после сохранения новой версии.
const versions = ref<Array<{ label: string, value: number }>>([])
async function loadVersions() {
  const template = await getTemplate(props.templateId)
  versions.value = template?.versions.map((v, i) => ({
    label: `Версия ${i + 1}${v.schema.updatedAt ? ' — ' + new Date(v.schema.updatedAt).toLocaleDateString() : ''}`,
    value: i + 1,
  })) ?? []
}
onMounted(() => {
  void loadVersions()
  arrangeOnceReady()
})

function onNodeClick({ node }: { node: { id: string } }) {
  selectedNodeId.value = node.id
  slideoverOpen.value = true
}

// ─── Подсветка связанных нод/рёбер при наведении (item 7 фидбека) ──────────
// Ноды получают состояние через provide/inject (useWorkflowHighlight) — без
// мутации persisted nodes.value, чтобы наведение не триггерило автосохранение.
// Рёбра стилизуются напрямую в DOM (та же причина): built-in smoothstep-эдж
// не читает состояние без мутации edges.value, а это провоцирует autosave.
const highlightIds = provideWorkflowHighlight()

function connectedEdgeIds(nodeId: string): Set<string> {
  return new Set(edges.value.filter((e) => e.source === nodeId || e.target === nodeId).map((e) => e.id))
}

function onNodeMouseEnter({ node }: { node: { id: string } }) {
  const ids = connectedEdgeIds(node.id)
  highlightIds.value = new Set([node.id, ...edges.value
    .filter((e) => ids.has(e.id))
    .flatMap((e) => [e.source, e.target])])

  const root = canvasEl.value
  if (!root) return
  root.classList.add('journal-builder__canvas--hover-active')
  root.querySelectorAll('.vue-flow__edge').forEach((el) => {
    const isConnected = ids.has(el.getAttribute('data-id') ?? '')
    el.classList.toggle('wf-edge--highlighted', isConnected)
    // «Бегущий пунктир» от источника к получателю — тот же класс, что и у
    // встроенного animated:true (путь SVG у Vue Flow всегда рисуется
    // source → target, поэтому направление анимации совпадает само собой).
    el.classList.toggle('animated', isConnected)
  })
}

function onNodeMouseLeave() {
  highlightIds.value = null
  const root = canvasEl.value
  if (!root) return
  root.classList.remove('journal-builder__canvas--hover-active')
  root.querySelectorAll('.wf-edge--highlighted').forEach((el) => {
    el.classList.remove('wf-edge--highlighted', 'animated')
  })
}

function applyLayout() {
  nodes.value = layout(nodes.value, edges.value)
  nextTick(() => fitView())
}

// Схема должна открываться уже упорядоченной (dagre TB), чтобы ноды не
// наезжали друг на друга и на рёбра — даже если сохранённые/старые позиции
// это допускали. Раскладка запускается по факту измерения реальных размеров
// нод (useNodesInitialized), а не по фиксированным заглушкам — иначе карточки
// разной высоты (условие с длинным правилом, шаг с многими полями) могли бы
// перекрываться из-за неточных dagre-размеров.
const nodesInitialized = useNodesInitialized()
function arrangeOnceReady() {
  if (nodesInitialized.value) {
    applyLayout()
    return
  }
  const stop = watch(nodesInitialized, (ready) => {
    if (ready) {
      applyLayout()
      stop()
    }
  })
}

// ─── Контекст-меню по ноде (right-click) ────────────────────────────────────
const contextNodeId = ref<string | null>(null)
const contextMenuOpen = ref(false)
const contextMenuPosition = ref({ x: 0, y: 0 })

function duplicateNode(id: string) {
  const source = nodes.value.find((n) => n.id === id)
  if (!source) return
  const dup: JournalNode = {
    ...cloneData(source),
    id: `${source.type}-${idCounter++}`,
    position: { x: source.position.x + 40, y: source.position.y + 40 },
  }
  nodes.value.push(dup)
  selectedNodeId.value = dup.id
  slideoverOpen.value = true
}

function addRelatedNode(id: string) {
  const source = nodes.value.find((n) => n.id === id)
  if (!source) return
  const newId = `step-${idCounter++}`
  const position = { x: source.position.x, y: source.position.y + 160 }
  nodes.value.push({
    id: newId,
    type: 'step',
    position,
    data: { label: 'Новый шаг', fields: [], screen: { rows: [] } } satisfies JournalStepData,
    dragHandle: DRAG_HANDLE_SELECTOR,
  })
  addEdges([{ id: `e-${id}-${newId}`, source: id, target: newId }])
  selectedNodeId.value = newId
  slideoverOpen.value = true
}

function deleteNode(id: string) {
  removeNodes([id], true)
  if (selectedNodeId.value === id) {
    selectedNodeId.value = null
    slideoverOpen.value = false
  }
}

const contextMenuItems = computed<DropdownMenuItem[]>(() => {
  const id = contextNodeId.value
  if (!id) return []
  const node = nodes.value.find((n) => n.id === id)
  // Старт/Финиш — по одному на схему, дублировать их бессмысленно (и опасно:
  // раннер/движок ожидают ровно один узел каждого типа).
  const isTerminal = node?.type === 'start' || node?.type === 'end'
  const items: DropdownMenuItem[] = [
    { label: 'Открыть', icon: 'i-lucide-square-pen', onSelect: () => { selectedNodeId.value = id; slideoverOpen.value = true } },
  ]
  if (!isTerminal) {
    items.push({ label: 'Дублировать', icon: 'i-lucide-copy', onSelect: () => duplicateNode(id) })
  }
  items.push({ label: 'Создать связанную', icon: 'i-lucide-git-branch-plus', onSelect: () => addRelatedNode(id) })
  if (!isTerminal) {
    items.push({ type: 'separator' }, { label: 'Удалить', icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => deleteNode(id) })
  }
  return items
})

async function openNodeMenu(id: string, event: MouseEvent) {
  event.preventDefault()
  contextNodeId.value = id
  contextMenuOpen.value = false
  contextMenuPosition.value = { x: event.clientX, y: event.clientY }
  await nextTick()
  contextMenuOpen.value = true
}

// «⋯» в шапке ноды (n8n-подобный референс) открывает то же меню, что и
// правый клик — единая точка входа для всех 5 компонентов нод (provide/inject).
provideWorkflowNodeMenu(openNodeMenu)

function onNodeContextMenu({ event, node }: NodeMouseEvent) {
  void openNodeMenu(node.id, event as MouseEvent)
}

onConnect((connection: Connection) => {
  addEdges([
    {
      id: `e-${connection.source}-${connection.target}-${connection.sourceHandle ?? 'default'}`,
      source: connection.source,
      target: connection.target,
      sourceHandle: connection.sourceHandle as 'true' | 'false' | undefined,
      label: branchLabel(connection.sourceHandle),
      class: branchClass(connection.sourceHandle),
    },
  ])
})

let idCounter = nodes.value.length + 1

function nextPosition() {
  const index = nodes.value.length
  return { x: 80, y: 40 + index * 160 }
}

function addStepNode() {
  const id = `step-${idCounter++}`
  nodes.value.push({
    id,
    type: 'step',
    position: nextPosition(),
    data: { label: 'Новый шаг', fields: [], screen: { rows: [] } } satisfies JournalStepData,
    dragHandle: DRAG_HANDLE_SELECTOR,
  })
  selectedNodeId.value = id
  slideoverOpen.value = true
}

function addConditionNode() {
  const id = `cond-${idCounter++}`
  nodes.value.push({
    id,
    type: 'condition',
    position: nextPosition(),
    data: { label: 'Новое условие', rule: { '==': [1, 1] } } satisfies JournalConditionData,
    dragHandle: DRAG_HANDLE_SELECTOR,
  })
  selectedNodeId.value = id
  slideoverOpen.value = true
}

function addLoopNode() {
  const id = `loop-${idCounter++}`
  nodes.value.push({
    id,
    type: 'loop',
    position: nextPosition(),
    data: { label: 'Новый цикл', itemNoun: 'тест', fields: [], screen: { rows: [] } } satisfies JournalLoopData,
    dragHandle: DRAG_HANDLE_SELECTOR,
  })
  selectedNodeId.value = id
  slideoverOpen.value = true
}

function deleteSelectedNode() {
  if (!selectedNode.value) return
  deleteNode(selectedNode.value.id)
}

// Экран выбранного step/loop-узла для ScreenEditor. Гарантированно материализован
// (ensureV2 при загрузке + новые узлы получают пустой screen), поэтому getter
// возвращает существующий объект; двусторонняя правка идёт в data.screen.
const activeScreen = computed<Screen>({
  get() {
    const node = selectedNode.value
    if (node?.type === 'step' || node?.type === 'loop') {
      const data = node.data as JournalStepData | JournalLoopData
      return data.screen ?? toScreen(data)
    }
    return { rows: [] }
  },
  set(value) {
    const node = selectedNode.value
    if (node?.type === 'step' || node?.type === 'loop') {
      (node.data as JournalStepData | JournalLoopData).screen = value
    }
  },
})

// Действия выбранного step-узла для StepActionsEditor. Массив может отсутствовать
// на старых схемах — первое добавление материализует data.actions.
const activeActions = computed<DomainAction[]>({
  get() {
    const node = selectedNode.value
    return node?.type === 'step' ? (node.data as JournalStepData).actions ?? [] : []
  },
  set(value) {
    const node = selectedNode.value
    if (node?.type === 'step') {
      (node.data as JournalStepData).actions = value
    }
  },
})

// Все поля схемы (по всем step/loop-экранам) — для выбора targetField и ссылок на
// ответы в редакторе действий. Действие шага «Результат» ссылается и на поля
// прошлых шагов (например test_id), поэтому список — по всей схеме, не только шагу.
const allFieldOptions = computed<Array<{ label: string, value: string }>>(() => {
  const seen = new Map<string, string>()
  for (const node of nodes.value) {
    if (node.type !== 'step' && node.type !== 'loop') continue
    const data = node.data as JournalStepData | JournalLoopData
    for (const field of screenFields(toScreen(data))) {
      if (!seen.has(field.id)) {
        seen.set(field.id, field.label || field.id)
      }
    }
  }
  return Array.from(seen, ([value, label]) => ({ label: `${label} (${value})`, value }))
})

function buildSchema(): JournalSchema {
  return {
    ...props.modelValue,
    nodes: nodes.value,
    edges: edges.value,
    updatedAt: new Date().toISOString(),
  }
}

function exportSchema() {
  const schema = buildSchema()
  emit('update:modelValue', schema)
  return schema
}

function saveCurrent() {
  const schema = exportSchema()
  // Черновик паркуется локально; коммит в иммутабельную версию — «Новая версия».
  void updateCurrentSchema(props.templateId, schema)
}

async function saveNewVersion() {
  const schema = exportSchema()
  const template = await saveSchemaVersion(props.templateId, schema)
  showVersionModal.value = false
  versionNote.value = ''
  await loadVersions()
  emit('version-saved', template.currentVersion)
}

async function loadVersion(version: number) {
  const schema = (await getSchemaVersions(props.templateId))[version - 1]
  if (!schema) return
  nodes.value = withDragHandle(cloneData(ensureV2(schema).nodes))
  edges.value = withBranchLabels(cloneData(schema.edges))
  selectedNodeId.value = null
  emit('update:modelValue', schema)
  arrangeOnceReady()
}

async function downloadTemplate() {
  const json = await exportTemplate(props.templateId)
  const blob = new Blob([json], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${props.modelValue.title || 'journal'}-template.json`
  a.click()
  URL.revokeObjectURL(url)
}

function importTemplateFile(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = async () => {
    try {
      const result = await importData(reader.result as string)
      await loadVersions()
      toast.add({
        title: 'Импорт завершён',
        description: `Шаблонов: ${result.templates}, записей: ${result.runs}`,
        color: 'success',
        icon: 'i-lucide-check',
      })
    } catch (e) {
      toast.add({
        title: 'Ошибка импорта',
        description: (e as Error).message,
        color: 'error',
        icon: 'i-lucide-circle-alert',
      })
    }
  }
  reader.readAsText(file)
}

// Автосохранение
watch([nodes, edges], () => {
  saveCurrent()
}, { deep: true })

defineExpose({ exportSchema, saveCurrent, saveNewVersion })
</script>

<template>
  <div class="journal-builder">
    <!-- Единая панель управления: все кнопки конструктора + версии + слот для
         действий страницы (пробный прогон/переименовать/удалить). -->
    <div class="journal-builder__toolbar">
      <div class="journal-builder__toolbar-group">
        <UButton icon="i-lucide-list-checks" size="sm" @click="addStepNode">
          Шаг
        </UButton>
        <UButton
          icon="i-lucide-git-branch"
          size="sm"
          color="neutral"
          variant="soft"
          @click="addConditionNode"
        >
          Условие
        </UButton>
        <UButton
          icon="i-lucide-repeat"
          size="sm"
          color="success"
          variant="soft"
          @click="addLoopNode"
        >
          Цикл
        </UButton>
        <UButton
          icon="i-lucide-network"
          size="sm"
          color="neutral"
          variant="soft"
          @click="applyLayout"
        >
          Упорядочить
        </UButton>
        <UButton
          icon="i-lucide-download"
          size="sm"
          color="neutral"
          variant="ghost"
          @click="downloadTemplate"
        >
          Скачать
        </UButton>
        <UButton
          icon="i-lucide-upload"
          size="sm"
          color="neutral"
          variant="ghost"
          @click="importInput?.click()"
        >
          Импорт
        </UButton>
        <input
          ref="importInput"
          type="file"
          accept=".json"
          class="hidden"
          @change="importTemplateFile"
        >
      </div>

      <div class="journal-builder__toolbar-group journal-builder__toolbar-group--end">
        <USelect
          v-if="versions.length > 1"
          :model-value="props.modelValue.version"
          :items="versions"
          size="xs"
          class="w-48"
          @update:model-value="loadVersion"
        />
        <UButton size="xs" variant="soft" @click="showVersionModal = true">
          Новая версия
        </UButton>
        <slot name="toolbar-end" />
      </div>
    </div>

    <div ref="canvasEl" class="journal-builder__canvas">
      <VueFlow
        v-model:nodes="nodes"
        v-model:edges="edges"
        :node-types="nodeTypes"
        :default-edge-options="{ type: 'smoothstep' }"
        :min-zoom="0.15"
        fit-view-on-init
        :fit-view-options="{ padding: 0.12 }"
        @node-click="onNodeClick"
        @node-context-menu="onNodeContextMenu"
        @node-mouse-enter="onNodeMouseEnter"
        @node-mouse-leave="onNodeMouseLeave"
      >
        <Background pattern-color="#aaa" :gap="16" />
        <Controls />
        <MiniMap pannable zoomable />
      </VueFlow>

      <RowContextMenu
        v-model:open="contextMenuOpen"
        :items="contextMenuItems"
        :x="contextMenuPosition.x"
        :y="contextMenuPosition.y"
      />
    </div>

    <!-- Инфо/редактор выбранной ноды — оверлей справа -->
    <WorkflowNodeSlideover
      v-if="selectedNode"
      v-model:open="slideoverOpen"
      :node="selectedNode"
      :screen="activeScreen"
      :actions="activeActions"
      :field-options="allFieldOptions"
      @update:screen="activeScreen = $event"
      @update:actions="activeActions = $event"
      @delete="deleteSelectedNode"
    />

    <!-- Модалка новой версии -->
    <UModal v-model:open="showVersionModal" title="Сохранить новую версию">
      <template #body>
        <p class="text-sm text-muted mb-3">
          Текущая версия: {{ props.modelValue.version }}. Новая версия будет {{ props.modelValue.version + 1 }}.
        </p>
        <UFormField label="Примечание к версии (опционально)">
          <UTextarea v-model="versionNote" :rows="2" placeholder="Что изменилось в этой версии..." />
        </UFormField>
      </template>
      <template #footer>
        <UButton variant="ghost" @click="showVersionModal = false">
          Отмена
        </UButton>
        <UButton @click="saveNewVersion">
          Сохранить версию {{ props.modelValue.version + 1 }}
        </UButton>
      </template>
    </UModal>
  </div>
</template>

<style scoped>
.journal-builder {
  display: flex;
  flex-direction: column;
  height: 100%;
  /* Пол высоты: контейнер-хост задаёт высоту через цепочку h-full не всегда
     (percentage height схлопывается при auto-высоте предка), а VueFlow без высоты
     не рендерит канвас. vh-floor гарантирует видимый граф в любом хосте. */
  min-height: min(72vh, 680px);
  overflow: hidden;
}
.journal-builder__toolbar {
  flex-shrink: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--ui-border);
  background: var(--ui-bg);
}
.journal-builder__toolbar-group {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
.journal-builder__toolbar-group--end {
  margin-left: auto;
}
.journal-builder__canvas {
  position: relative;
  flex: 1;
  min-height: 0;
  background: var(--ui-bg-muted);
}
</style>