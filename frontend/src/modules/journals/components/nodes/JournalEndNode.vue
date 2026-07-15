<script setup lang="ts">
// components/journal/nodes/JournalEndNode.vue
import { Handle, Position } from '@vue-flow/core';

defineProps<{
  data: { label: string }
  selected?: boolean
}>()
</script>

<template>
  <div class="wf-node wf-node--end wf-node--terminal" :class="{ 'wf-node--selected': selected }">
    <Handle type="target" :position="Position.Left" />

    <div class="wf-node__header">
      <span class="wf-node__icon">
        <UIcon name="i-lucide-flag" class="size-4" />
      </span>
      <div class="wf-node__heading">
        <span class="wf-node__kicker">Финиш</span>
        <span class="wf-node__title">{{ data.label }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.wf-node--terminal {
  min-width: 150px;
}
</style>
