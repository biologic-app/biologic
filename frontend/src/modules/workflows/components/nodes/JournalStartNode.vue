<script setup lang="ts">
// components/nodes/JournalStartNode.vue
import { computed } from 'vue';
import { Handle, Position } from '@vue-flow/core';
import { useWorkflowNodeDimmed } from '@/modules/workflows/composables/useWorkflowHighlight';
import { useWorkflowNodeMenu } from '@/modules/workflows/composables/useWorkflowNodeMenu';
import type { JournalStartData, JournalStartTrigger } from '@/modules/workflows/types/journal';

const props = defineProps<{
  id: string
  data: JournalStartData
  selected?: boolean
}>()

const dimmed = useWorkflowNodeDimmed(computed(() => props.id))
const openNodeMenu = useWorkflowNodeMenu()

const TRIGGER_LABELS: Record<JournalStartTrigger, string> = {
  manual: 'Ручной',
}
// Схемы, сохранённые до появления поля, читаются как 'manual' по умолчанию.
const triggerLabel = computed(() => TRIGGER_LABELS[props.data.trigger ?? 'manual'])
</script>

<template>
  <div
    class="wf-node wf-node--start wf-node--terminal"
    :class="{ 'wf-node--selected': selected, 'wf-node--dimmed': dimmed }"
  >
    <div class="wf-node__header">
      <div class="wf-node__header-row">
        <span class="wf-node__icon">
          <UIcon name="i-lucide-play" class="size-4" />
        </span>
        <div class="wf-node__heading">
          <span class="wf-node__title">{{ data.label }}</span>
        </div>
        <button type="button" class="wf-node__menu" @click.stop="openNodeMenu(id, $event)">
          <UIcon name="i-lucide-grip-vertical" class="size-3.5" />
        </button>
      </div>
    </div>

    <div class="wf-node__body">
      <div class="wf-field">
        <UIcon name="i-lucide-mouse-pointer-click" class="wf-field__icon" />
        <span class="wf-field__name">Триггер</span>
        <span class="wf-field__type">{{ triggerLabel }}</span>
      </div>
    </div>

    <Handle type="source" :position="Position.Bottom" />
  </div>
</template>

<style scoped>
.wf-node--terminal {
  min-width: 150px;
}
</style>
