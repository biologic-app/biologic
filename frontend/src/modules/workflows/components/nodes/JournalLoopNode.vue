<script setup lang="ts">
// components/nodes/JournalLoopNode.vue
// Циклическая нода: повторяемый шаг с ручным выходом.
import { Handle, Position } from '@vue-flow/core';
import type { JournalLoopData } from '@/modules/workflows/types/journal';

defineProps<{
  data: JournalLoopData
  selected?: boolean
}>()
</script>

<template>
  <div class="wf-node wf-node--loop" :class="{ 'wf-node--selected': selected }">
    <Handle type="target" :position="Position.Top" />

    <!-- декоративная дуга «цикла» над нодой -->
    <span class="wf-loop__arc" aria-hidden="true">
      <UIcon name="i-lucide-rotate-cw" class="size-3.5" />
    </span>

    <div class="wf-node__header">
      <span class="wf-node__icon">
        <UIcon name="i-lucide-repeat" class="size-4" />
      </span>
      <div class="wf-node__heading">
        <span class="wf-node__kicker">Цикл · повтор вручную</span>
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

      <div class="wf-loop__note">
        <UIcon name="i-lucide-infinity" class="size-3.5" />
        <span>{{ data.itemNoun ? `Кол-во «${data.itemNoun}»` : 'Число итераций' }} — на усмотрение пользователя</span>
      </div>
    </div>

    <Handle type="source" :position="Position.Bottom" />
  </div>
</template>

<style scoped>
.wf-loop__arc {
  position: absolute;
  top: -13px;
  left: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  color: var(--ui-success);
  background: var(--ui-bg);
  border: 1.5px solid color-mix(in oklab, var(--ui-success) 55%, var(--ui-border));
}
.wf-loop__note {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 6px;
  padding: 5px 8px;
  border-radius: var(--ui-radius);
  font-size: 10.5px;
  font-weight: 500;
  color: var(--ui-success);
  background: color-mix(in oklab, var(--ui-success) 10%, transparent);
}
</style>
