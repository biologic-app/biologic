<script setup lang="ts">
// components/nodes/JournalEndNode.vue
import { computed } from 'vue';
import { Handle, Position } from '@vue-flow/core';
import { useWorkflowNodeDimmed } from '@/modules/workflows/composables/useWorkflowHighlight';
import { useWorkflowNodeMenu } from '@/modules/workflows/composables/useWorkflowNodeMenu';

const props = defineProps<{
  id: string
  data: { label: string }
  selected?: boolean
}>()

const dimmed = useWorkflowNodeDimmed(computed(() => props.id))
const openNodeMenu = useWorkflowNodeMenu()
</script>

<template>
  <div
    class="wf-node wf-node--end wf-node--terminal"
    :class="{ 'wf-node--selected': selected, 'wf-node--dimmed': dimmed }"
  >
    <Handle type="target" :position="Position.Top" />

    <div class="wf-node__header">
      <div class="wf-node__header-row">
        <span class="wf-node__icon">
          <UIcon name="i-lucide-flag" class="size-4" />
        </span>
        <div class="wf-node__heading">
          <span class="wf-node__title">{{ data.label }}</span>
        </div>
        <button type="button" class="wf-node__menu" @click.stop="openNodeMenu(id, $event)">
          <UIcon name="i-lucide-grip-vertical" class="size-3.5" />
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.wf-node--terminal {
  min-width: 150px;
}
</style>
