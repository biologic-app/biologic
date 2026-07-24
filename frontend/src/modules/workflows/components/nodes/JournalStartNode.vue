<script setup lang="ts">
// components/nodes/JournalStartNode.vue
import { Handle, Position } from '@vue-flow/core';

defineProps<{
  data: { label: string }
  selected?: boolean
}>()
</script>

<template>
  <div class="wf-node wf-node--start wf-node--terminal" :class="{ 'wf-node--selected': selected }">
    <div class="wf-node__header">
      <span class="wf-node__icon">
        <UIcon name="i-lucide-play" class="size-4" />
      </span>
      <div class="wf-node__heading">
        <span class="wf-node__kicker">Старт</span>
        <span class="wf-node__title">{{ data.label }}</span>
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
