<script setup lang="ts">
withDefaults(
  defineProps<{
    title?: string;
    description?: string;
    filtered?: boolean;
    error?: boolean;
    errorDescription?: string;
  }>(),
  {
    title: "Нет данных",
    description: "Измените фильтры или создайте новую запись.",
    filtered: false,
    error: false,
    errorDescription: "Попробуйте обновить страницу или повторите попытку позже.",
  },
);

const emit = defineEmits<{
  (e: "clearFilters"): void;
  (e: "retry"): void;
}>();
</script>

<template>
  <div class="flex min-h-[min(34rem,calc(100vh-18rem))] w-full flex-col items-center justify-center gap-4 px-8 py-16 text-center">
    <div
      class="flex size-16 items-center justify-center rounded-full border"
      :class="error ? 'border-error/30 bg-error/5' : 'border-default bg-elevated'"
    >
      <UIcon
        :name="error ? 'i-lucide-triangle-alert' : filtered ? 'i-lucide-search-x' : 'i-lucide-inbox'"
        class="size-7"
        :class="error ? 'text-error' : 'text-muted'"
      />
    </div>
    <div class="space-y-2">
      <p class="text-lg font-semibold text-highlighted">
        {{ error ? "Ошибка загрузки" : title }}
      </p>
      <p class="max-w-md text-base text-muted">
        {{ error ? errorDescription : description }}
      </p>
    </div>
    <div v-if="filtered || error" class="flex items-center gap-2">
      <UButton
        v-if="filtered"
        color="neutral"
        variant="outline"
        size="sm"
        icon="i-lucide-filter-x"
        label="Сбросить фильтры"
        @click="emit('clearFilters')"
      />
      <UButton
        v-if="error"
        color="neutral"
        variant="outline"
        size="sm"
        icon="i-lucide-refresh-cw"
        label="Повторить"
        @click="emit('retry')"
      />
    </div>
  </div>
</template>
