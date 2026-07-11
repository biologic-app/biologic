<script setup lang="ts">
defineProps<{ items: Array<{ label: string }> }>();
const emit = defineEmits<{ (e: "go-to-level", index: number): void }>();
</script>

<template>
  <UBreadcrumb v-if="items.length" :items="items" class="min-w-0">
    <template #item-label="{ item: crumb, index }">
      <button
        type="button"
        class="truncate"
        :class="index === items.length - 1
          ? 'cursor-default text-highlighted'
          : 'cursor-pointer text-muted hover:text-primary'"
        :disabled="index === items.length - 1"
        @click="emit('go-to-level', index)"
      >
        {{ crumb.label }}
      </button>
    </template>
  </UBreadcrumb>
</template>
