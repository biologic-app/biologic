<script setup lang="ts">
// components/journal/JournalBuilder.vue
// Конструктор с графическим редактором правил

import { computed, markRaw, ref, toRaw, watch } from 'vue'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { Panel, VueFlow, useVueFlow, type Connection, type NodeTypesObject } from '@vue-flow/core'
import {
  exportTemplate,
  getSchemaVersions,
  getTemplate,
  importData,
  saveSchemaVersion,
  updateCurrentSchema,
} from '@/modules/journals/composables/useJournalStorage'
import type { JournalConditionData, JournalEdge, JournalLoopData, JournalNode, JournalSchema, JournalStepData } from '@/modules/journals/types/journal'
import JournalConditionNode from './nodes/JournalConditionNode.vue'
import JournalEndNode from './nodes/JournalEndNode.vue'
import JournalLoopNode from './nodes/JournalLoopNode.vue'
import JournalStartNode from './nodes/JournalStartNode.vue'
import JournalStepNode from './nodes/JournalStepNode.vue'
import RuleBuilder from './RuleBuilder.vue'

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

const nodeTypeLabels: Record<string, string> = {
  start: 'Старт',
  step: 'Шаг',
  condition: 'Условие',
  loop: 'Цикл',
  end: 'Финиш',
}

const { onConnect, addEdges, removeNodes } = useVueFlow()

const nodes = ref<JournalNode[]>(structuredClone(toRaw(props.modelValue.nodes)))
const edges = ref<JournalEdge[]>(structuredClone(toRaw(props.modelValue.edges)))
const selectedNodeId = ref<string | null>(null)
const showVersionModal = ref(false)
const versionNote = ref('')
const importInput = ref<HTMLInputElement | null>(null)

const selectedNode = computed(() => nodes.value.find((n) => n.id === selectedNodeId.value) ?? null)

// Загрузка версий
const versions = computed(() => {
  const template = getTemplate(props.templateId)
  return template?.versions.map((v, i) => ({
    label: `Версия ${i + 1}${v.schema.updatedAt ? ' — ' + new Date(v.schema.updatedAt).toLocaleDateString() : ''}`,
    value: i + 1,
  })) ?? []
})

function onNodeClick({ node }: { node: { id: string } }) {
  selectedNodeId.value = node.id
}

onConnect((connection: Connection) => {
  addEdges([
    {
      id: `e-${connection.source}-${connection.target}-${connection.sourceHandle ?? 'default'}`,
      source: connection.source,
      target: connection.target,
      sourceHandle: connection.sourceHandle as 'true' | 'false' | undefined,
    },
  ])
})

let idCounter = nodes.value.length + 1

function nextPosition() {
  const index = nodes.value.length
  const col = index % 4
  const row = Math.floor(index / 4)
  return { x: 80 + col * 240, y: 40 + row * 160 }
}

function addStepNode() {
  const id = `step-${idCounter++}`
  nodes.value.push({
    id,
    type: 'step',
    position: nextPosition(),
    data: { label: 'Новый шаг', fields: [] } satisfies JournalStepData,
  })
  selectedNodeId.value = id
}

function addConditionNode() {
  const id = `cond-${idCounter++}`
  nodes.value.push({
    id,
    type: 'condition',
    position: nextPosition(),
    data: { label: 'Новое условие', rule: { '==': [1, 1] } } satisfies JournalConditionData,
  })
  selectedNodeId.value = id
}

function addLoopNode() {
  const id = `loop-${idCounter++}`
  nodes.value.push({
    id,
    type: 'loop',
    position: nextPosition(),
    data: { label: 'Новый цикл', itemNoun: 'тест', fields: [] } satisfies JournalLoopData,
  })
  selectedNodeId.value = id
}

function deleteSelectedNode() {
  if (!selectedNode.value) return
  removeNodes([selectedNode.value.id], true)
  selectedNodeId.value = null
}

function addField() {
  if (selectedNode.value?.type !== 'step' && selectedNode.value?.type !== 'loop') return
  const data = selectedNode.value.data as JournalStepData | JournalLoopData
  data.fields.push({ id: `field-${Date.now()}`, label: 'Новое поле', type: 'text', required: true })
}

function removeField(fieldId: string) {
  if (selectedNode.value?.type !== 'step' && selectedNode.value?.type !== 'loop') return
  const data = selectedNode.value.data as JournalStepData | JournalLoopData
  data.fields = data.fields.filter((f) => f.id !== fieldId)
}

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
  updateCurrentSchema(props.templateId, schema)
}

function saveNewVersion() {
  const schema = exportSchema()
  saveSchemaVersion(props.templateId, schema)
  showVersionModal.value = false
  versionNote.value = ''
  emit('version-saved', schema.version)
}

function loadVersion(version: number) {
  const schema = getSchemaVersions(props.templateId)[version - 1]
  if (!schema) return
  nodes.value = structuredClone(toRaw(schema.nodes))
  edges.value = structuredClone(toRaw(schema.edges))
  emit('update:modelValue', schema)
}

function downloadTemplate() {
  const json = exportTemplate(props.templateId)
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
  reader.onload = () => {
    try {
      const result = importData(reader.result as string)
      toast.add({
        title: 'Импорт завершён',
        description: `Шаблонов: ${result.templates}, записей: ${result.entries}`,
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
    <div class="journal-builder__canvas">
      <VueFlow
        v-model:nodes="nodes"
        v-model:edges="edges"
        :node-types="nodeTypes"
        :default-edge-options="{ type: 'smoothstep' }"
        :min-zoom="0.15"
        fit-view-on-init
        :fit-view-options="{ padding: 0.12 }"
        @node-click="onNodeClick"
      >
        <Background pattern-color="#aaa" :gap="16" />
        <Controls />

        <Panel position="top-left" class="journal-builder__toolbar">
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
        </Panel>

        <Panel position="top-right" class="journal-builder__version-panel">
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
        </Panel>
      </VueFlow>
    </div>

    <aside class="journal-builder__inspector">
      <template v-if="selectedNode">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-sm font-semibold">
            {{ nodeTypeLabels[selectedNode.type] ?? selectedNode.type }}
          </h3>
          <UButton
            v-if="selectedNode.type !== 'start' && selectedNode.type !== 'end'"
            size="xs"
            color="error"
            variant="ghost"
            icon="i-lucide-trash-2"
            @click="deleteSelectedNode"
          >
            Удалить
          </UButton>
        </div>

        <UFormField label="Название" size="sm">
          <UInput v-model="(selectedNode.data as any).label" size="sm" />
        </UFormField>

        <!-- ШАГ -->
        <template v-if="selectedNode.type === 'step'">
          <UFormField label="Описание" size="sm" class="mt-2">
            <UInput v-model="(selectedNode.data as JournalStepData).description" size="sm" />
          </UFormField>
          <UFormField label="Роль" size="sm" class="mt-2">
            <UInput v-model="(selectedNode.data as JournalStepData).role" size="sm" placeholder="например: lab_assistant" />
          </UFormField>

          <div class="mt-4 mb-2 flex items-center justify-between">
            <span class="text-xs font-medium text-muted">Поля</span>
            <UButton
              size="xs"
              variant="ghost"
              icon="i-lucide-plus"
              @click="addField"
            >
              Добавить
            </UButton>
          </div>
          <div v-for="field in (selectedNode.data as JournalStepData).fields" :key="field.id" class="journal-builder__field">
            <UInput v-model="field.label" size="xs" class="flex-1" />
            <USelect
              v-model="field.type"
              :items="['text', 'number', 'boolean', 'select', 'date', 'textarea']"
              size="xs"
              class="w-28"
            />
            <UButton
              size="xs"
              color="error"
              variant="ghost"
              icon="i-lucide-trash-2"
              @click="removeField(field.id)"
            />
          </div>
        </template>

        <!-- ЦИКЛ — как шаг, но повторяемый вручную -->
        <template v-if="selectedNode.type === 'loop'">
          <UFormField label="Описание" size="sm" class="mt-2">
            <UInput v-model="(selectedNode.data as JournalLoopData).description" size="sm" />
          </UFormField>
          <UFormField label="Роль" size="sm" class="mt-2">
            <UInput v-model="(selectedNode.data as JournalLoopData).role" size="sm" placeholder="например: doctor" />
          </UFormField>
          <UFormField
            label="Название итерации"
            size="sm"
            class="mt-2"
            help="Как называть одну итерацию: «тест», «проба»…"
          >
            <UInput v-model="(selectedNode.data as JournalLoopData).itemNoun" size="sm" placeholder="тест" />
          </UFormField>

          <div class="mt-4 mb-2 flex items-center justify-between">
            <span class="text-xs font-medium text-muted">Поля одной итерации</span>
            <UButton
              size="xs"
              variant="ghost"
              icon="i-lucide-plus"
              @click="addField"
            >
              Добавить
            </UButton>
          </div>
          <div v-for="field in (selectedNode.data as JournalLoopData).fields" :key="field.id" class="journal-builder__field">
            <UInput v-model="field.label" size="xs" class="flex-1" />
            <USelect
              v-model="field.type"
              :items="['text', 'number', 'boolean', 'select', 'date', 'textarea']"
              size="xs"
              class="w-28"
            />
            <UButton
              size="xs"
              color="error"
              variant="ghost"
              icon="i-lucide-trash-2"
              @click="removeField(field.id)"
            />
          </div>
        </template>

        <!-- УСЛОВИЕ — графический конструктор -->
        <template v-if="selectedNode.type === 'condition'">
          <div class="mt-4">
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs font-medium text-muted">Правило</span>
            </div>
            <RuleBuilder
              v-model="(selectedNode.data as JournalConditionData).rule"
            />
          </div>
        </template>
      </template>

      <p v-else class="text-sm text-muted">
        Выберите ноду на канвасе, чтобы отредактировать её. Чтобы соединить ноды — потяните
        от кружка-хэндла на правом краю одной ноды к хэндлу на левом краю другой.
      </p>
    </aside>

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
  display: grid;
  grid-template-columns: 1fr 340px;
  height: 100%;
  min-height: 0;
  border: 1px solid var(--ui-border);
  border-radius: 12px;
  overflow: hidden;
}
.journal-builder__canvas {
  position: relative;
  background: var(--ui-bg-muted);
}
.journal-builder__toolbar {
  display: flex;
  gap: 6px;
}
.journal-builder__version-panel {
  display: flex;
  gap: 8px;
  align-items: center;
}
.journal-builder__inspector {
  border-left: 1px solid var(--ui-border);
  padding: 16px;
  overflow-y: auto;
  background: var(--ui-bg);
}
.journal-builder__field {
  display: flex;
  gap: 4px;
  align-items: center;
  margin-bottom: 6px;
}
</style>