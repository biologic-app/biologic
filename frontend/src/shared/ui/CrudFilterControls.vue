<script setup lang="ts">
withDefaults(
  defineProps<{
    activeCount?: number;
    label?: string;
    clearTooltip?: string;
  }>(),
  {
    activeCount: 0,
    label: "Фильтр",
    clearTooltip: "Сбросить фильтры",
  },
);

const emit = defineEmits<{
  (event: "open"): void;
  (event: "clear"): void;
}>();
</script>

<template>
  <UFieldGroup>
    <UButton
      :label="label"
      color="neutral"
      variant="subtle"
      icon="i-lucide-filter"
      @click="emit('open')"
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
