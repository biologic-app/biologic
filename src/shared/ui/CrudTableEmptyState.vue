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
  <div class="flex min-h-[min(34rem,calc(100vh-18rem))] w-full items-center justify-center px-8 py-16">
    <UEmpty
      v-if="error"
      variant="naked"
      size="xl"
      icon="i-lucide-cloud-off"
      title="Не удалось загрузить данные"
      :description="errorDescription"
      class="max-w-xl"
    >
      <template #actions>
        <UButton
          color="neutral"
          variant="outline"
          size="sm"
          icon="i-lucide-refresh-cw"
          label="Повторить"
          @click="emit('retry')"
        />
      </template>
    </UEmpty>

    <UEmpty
      v-else
      variant="naked"
      size="xl"
      :icon="filtered ? 'i-lucide-search-x' : 'i-lucide-inbox'"
      :title="title"
      :description="description"
      class="max-w-xl"
    >
      <template
        v-if="filtered"
        #actions
      >
        <UButton
          color="neutral"
          variant="outline"
          size="sm"
          icon="i-lucide-filter-x"
          label="Сбросить фильтры"
          @click="emit('clearFilters')"
        />
      </template>
    </UEmpty>
  </div>
</template>
