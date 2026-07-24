<script setup lang="ts">
// components/WorkflowNodeSlideover.vue
// Инфо/редактор выбранной ноды канваса — вынесено из инлайн-колонки JournalBuilder
// в оверлей (US-канвас-редизайн §4). Двусторонняя правка (label/description/role,
// screen, actions, rule) остаётся как есть — это move, не rewrite.
import { computed } from 'vue'
import type { DomainAction, JournalConditionData, JournalLoopData, JournalNode, JournalStepData, Screen } from '@/modules/workflows/types/journal'
import RuleBuilder from './RuleBuilder.vue'
import ScreenEditor from './ScreenEditor.vue'
import StepActionsEditor from './StepActionsEditor.vue'

const props = defineProps<{
  node: JournalNode
  screen: Screen
  actions: DomainAction[]
  fieldOptions: Array<{ label: string, value: string }>
}>()

const emit = defineEmits<{
  'update:screen': [Screen]
  'update:actions': [DomainAction[]]
  delete: []
}>()

const open = defineModel<boolean>('open', { default: false })

const nodeTypeLabels: Record<string, string> = {
  start: 'Старт',
  step: 'Шаг',
  condition: 'Условие',
  loop: 'Цикл',
  end: 'Финиш',
}

const isScreenNode = computed(() => props.node.type === 'step' || props.node.type === 'loop')

const screenModel = computed<Screen>({
  get: () => props.screen,
  set: (value) => emit('update:screen', value),
})

const actionsModel = computed<DomainAction[]>({
  get: () => props.actions,
  set: (value) => emit('update:actions', value),
})
</script>

<template>
  <USlideover
    v-model:open="open"
    :title="nodeTypeLabels[node.type] ?? node.type"
    :ui="{ content: 'max-w-md sm:max-w-xl' }"
  >
    <template #body>
      <div class="wf-slideover__head">
        <div class="flex items-center justify-between mb-3">
          <UButton
            v-if="node.type !== 'start' && node.type !== 'end'"
            size="xs"
            color="error"
            variant="ghost"
            icon="i-lucide-trash-2"
            @click="emit('delete')"
          >
            Удалить
          </UButton>
        </div>

        <UFormField label="Название" size="sm">
          <UInput v-model="(node.data as any).label" size="sm" />
        </UFormField>

        <template v-if="node.type === 'step'">
          <UFormField label="Описание" size="sm" class="mt-2">
            <UInput v-model="(node.data as JournalStepData).description" size="sm" />
          </UFormField>
          <UFormField label="Роль" size="sm" class="mt-2">
            <UInput
              v-model="(node.data as JournalStepData).role"
              size="sm"
              placeholder="например: lab_assistant"
            />
          </UFormField>
        </template>

        <template v-if="node.type === 'loop'">
          <UFormField label="Описание" size="sm" class="mt-2">
            <UInput v-model="(node.data as JournalLoopData).description" size="sm" />
          </UFormField>
          <UFormField label="Роль" size="sm" class="mt-2">
            <UInput
              v-model="(node.data as JournalLoopData).role"
              size="sm"
              placeholder="например: doctor"
            />
          </UFormField>
          <UFormField
            label="Название итерации"
            size="sm"
            class="mt-2"
            help="Как называть одну итерацию: «тест», «проба»…"
          >
            <UInput
              v-model="(node.data as JournalLoopData).itemNoun"
              size="sm"
              placeholder="тест"
            />
          </UFormField>
        </template>
      </div>

      <!-- ШАГ / ЦИКЛ — редактор экрана (грид со слотами) + действия шага -->
      <div v-if="isScreenNode" class="wf-slideover__screen">
        <ScreenEditor :key="node.id" v-model="screenModel" />
        <template v-if="node.type === 'step'">
          <USeparator class="my-4" />
          <StepActionsEditor
            :key="`actions-${node.id}`"
            v-model="actionsModel"
            :field-options="fieldOptions"
          />
        </template>
      </div>

      <!-- УСЛОВИЕ — графический конструктор правила -->
      <div v-else-if="node.type === 'condition'" class="wf-slideover__rule">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-medium text-muted">Правило</span>
        </div>
        <RuleBuilder v-model="(node.data as JournalConditionData).rule" />
      </div>
    </template>
  </USlideover>
</template>

<style scoped>
.wf-slideover__head {
  padding-bottom: 12px;
  border-bottom: 1px solid var(--ui-border);
}
.wf-slideover__screen,
.wf-slideover__rule {
  padding-top: 12px;
}
</style>
