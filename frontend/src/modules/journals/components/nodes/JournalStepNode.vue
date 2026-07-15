<script setup lang="ts">
// components/journal/nodes/JournalStepNode.vue
import { Handle, Position } from '@vue-flow/core';
import type { JournalStepData } from '@/modules/journals/types/journal';

defineProps<{
  data: JournalStepData
  selected?: boolean
}>()
</script>

<template>
  <div class="wf-node wf-node--step" :class="{ 'wf-node--selected': selected }">
    <Handle type="target" :position="Position.Left" />

    <div class="wf-node__header">
      <span class="wf-node__icon">
        <UIcon name="i-lucide-list-checks" class="size-4" />
      </span>
      <div class="wf-node__heading">
        <span class="wf-node__kicker">Шаг</span>
        <span class="wf-node__title">{{ data.label }}</span>
      </div>
    </div>

    <div v-if="data.description" class="wf-node__desc">
      {{ data.description }}
    </div>

    <div class="wf-node__body">
      <div v-for="field in data.fields" :key="field.id" class="wf-field">
        <span class="wf-field__dot" :class="{ 'wf-field__dot--required': field.required }" />
        <span class="wf-field__name">{{ field.label }}</span>
        <span class="wf-field__type">{{ field.type }}</span>
      </div>
      <p v-if="!data.fields.length" class="wf-node__empty">
        Нет полей
      </p>
    </div>

    <Handle type="source" :position="Position.Right" />
  </div>
</template>
