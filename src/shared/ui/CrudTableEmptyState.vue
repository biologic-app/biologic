<script setup lang="ts">
withDefaults(
  defineProps<{
    title?: string;
    description?: string;
  }>(),
  {
    title: "Нет данных",
    description: "Измените фильтры или создайте новую запись.",
  },
);
</script>

<template>
  <div class="flex min-h-48 flex-col items-center justify-center gap-3 px-6 py-10 text-center">
    <div class="flex size-11 items-center justify-center rounded-full border border-default bg-elevated">
      <UIcon name="i-lucide-inbox" class="size-5 text-muted" />
    </div>
    <div class="space-y-1">
      <p class="text-sm font-semibold text-highlighted">
        {{ title }}
      </p>
      <p class="max-w-sm text-sm text-muted">
        {{ description }}
      </p>
    </div>
  </div>
</template>
