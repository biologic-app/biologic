<script setup lang="ts">
withDefaults(
  defineProps<{
    activeCount?: number;
    open?: boolean;
    label?: string;
    clearTooltip?: string;
  }>(),
  {
    activeCount: 0,
    open: false,
    label: "Фильтр",
    clearTooltip: "Сбросить фильтры",
  },
);

const emit = defineEmits<{
  (event: "toggle"): void;
  (event: "clear"): void;
}>();
</script>

<template>
  <UFieldGroup>
    <UButton
      :label="label"
      color="neutral"
      variant="subtle"
      :icon="open ? 'i-lucide-chevron-up' : 'i-lucide-filter'"
      @click="emit('toggle')"
    >
      <template v-if="activeCount > 0" #trailing>
        <UKbd>{{ activeCount }}</UKbd>
      </template>
    </UButton>

    <UTooltip :text="clearTooltip">
      <UButton
        color="neutral"
        variant="subtle"
        size="sm"
        class="px-2"
        icon="i-lucide-filter-x"
        @click="emit('clear')"
      />
    </UTooltip>
  </UFieldGroup>
</template>
