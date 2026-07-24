<script setup lang="ts">
// components/nodes/JournalStepNode.vue
import { useWorkflowNodeDimmed } from '@/modules/workflows/composables/useWorkflowHighlight';
import { useWorkflowNodeMenu } from '@/modules/workflows/composables/useWorkflowNodeMenu';
import { fieldTypeIcon } from '@/modules/workflows/engine/field-icons';
import type { JournalStepData } from '@/modules/workflows/types/journal';
import { Handle, Position } from '@vue-flow/core';
import { computed } from 'vue';

const props = defineProps<{
  id: string
  data: JournalStepData
  selected?: boolean
}>()

const dimmed = useWorkflowNodeDimmed(computed(() => props.id))
const openNodeMenu = useWorkflowNodeMenu()
</script>

<template>
  <div
    class="wf-node wf-node--step"
    :class="{ 'wf-node--selected': selected, 'wf-node--dimmed': dimmed }"
  >
    <Handle type="target" :position="Position.Top" />

    <div class="wf-node__header">
      <div class="wf-node__header-row">
        <span class="wf-node__icon">
          <UIcon name="i-lucide-list-todo" class="size-4" />
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
      <div v-for="field in data.fields" :key="field.id" class="wf-field">
        <UIcon :name="fieldTypeIcon(field.type)" class="wf-field__icon" />
        <span class="wf-field__name">{{ field.label }}</span>
        <span class="wf-field__type">{{ field.type }}</span>
      </div>
      <p v-if="!data.fields.length" class="wf-node__empty">
        Нет полей
      </p>
    </div>

    <Handle type="source" :position="Position.Bottom" />
  </div>
</template>
