<script setup lang="ts">
// components/nodes/JournalLoopNode.vue
// Циклическая нода: повторяемый шаг с ручным выходом.
import { useWorkflowNodeDimmed } from '@/modules/workflows/composables/useWorkflowHighlight';
import { useWorkflowNodeMenu } from '@/modules/workflows/composables/useWorkflowNodeMenu';
import { fieldTypeIcon } from '@/modules/workflows/engine/field-icons';
import type { JournalLoopData } from '@/modules/workflows/types/journal';
import { Handle, Position } from '@vue-flow/core';
import { computed } from 'vue';

const props = defineProps<{
  id: string
  data: JournalLoopData
  selected?: boolean
}>()

const dimmed = useWorkflowNodeDimmed(computed(() => props.id))
const openNodeMenu = useWorkflowNodeMenu()
</script>

<template>
  <div
    class="wf-node wf-node--loop"
    :class="{ 'wf-node--selected': selected, 'wf-node--dimmed': dimmed }"
  >
    <Handle type="target" :position="Position.Top" />




    <div class="wf-node__header">
      <div class="wf-node__header-row">
        <span class="wf-node__icon">
          <UIcon name="i-lucide-repeat-2" class="size-4" />
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

      <div class="wf-loop__note">
        <UIcon name="i-lucide-infinity" class="size-3.5" />
        <span>{{ data.itemNoun ? `Кол-во «${data.itemNoun}»` : 'Число итераций' }} — на усмотрение пользователя</span>
      </div>
    </div>

    <Handle type="source" :position="Position.Bottom" />
  </div>
</template>

<style scoped>
.wf-loop__loopback {
  position: absolute;
  top: 0;
  right: -15px;
  width: 20px;
  height: 100%;
  overflow: visible;
  pointer-events: none;
}
.wf-loop__loopback-path {
  /* Тот же вид, что у обычных рёбер канваса (.vue-flow__edge-path) — чтобы
     self-loop читался как настоящее ребро, а не декоративная дуга. */
  stroke: var(--ui-text-highlighted);
  stroke-width: 1.75;
  stroke-linecap: round;
}
.wf-loop__note {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 2px;
  padding: 5px 8px;
  border-radius: var(--ui-radius);
  font-size: 10.5px;
  font-weight: 500;
  color: var(--ui-text-muted);
  background: var(--ui-bg-muted);
}
</style>
