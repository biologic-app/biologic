<script setup lang="ts">
defineProps<{
  open: boolean;
  activeCount?: number;
}>();

const emit = defineEmits<{
  (e: "update:open", value: boolean): void;
  (e: "apply"): void;
  (e: "reset"): void;
}>();
</script>

<template>
  <UModal
    :open="open"
    title="Фильтры"
    :ui="{ content: 'max-w-3xl' }"
    @update:open="emit('update:open', $event)"
  >
    <template #body>
      <div class="grid gap-3">
        <slot />
      </div>
    </template>

    <template #footer>
      <div class="flex w-full items-center justify-between gap-3">
        <UButton
          color="neutral"
          variant="ghost"
          icon="i-lucide-filter-x"
          label="Сбросить"
          @click="emit('reset')"
        />
        <div class="flex items-center gap-3">
          <UButton
            color="neutral"
            variant="ghost"
            label="Закрыть"
            @click="emit('update:open', false)"
          />
          <UButton
            label="Применить"
            icon="i-lucide-filter"
            @click="emit('apply'); emit('update:open', false)"
          />
        </div>
      </div>
    </template>
  </UModal>
</template>
