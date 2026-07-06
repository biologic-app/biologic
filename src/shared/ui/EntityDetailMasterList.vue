<script setup lang="ts">
import { ref } from "vue";
import { useInfiniteScroll } from "@vueuse/core";

export type DetailListColor =
  | "primary"
  | "info"
  | "success"
  | "warning"
  | "error"
  | "neutral";

export type DetailListItem = {
  id: string | number;
  title: string;
  subtitle?: string;
  color?: DetailListColor;
};

// Левый master-список детальной модалки с бесконечным скроллом.
// Доменно-нейтрален: получает уже нормализованные записи и события наверх.
const props = withDefaults(
  defineProps<{
    items: DetailListItem[];
    selectedId?: string | number | null;
    hasMore?: boolean;
    loadingMore?: boolean;
    label?: string;
  }>(),
  {
    selectedId: null,
    hasMore: false,
    loadingMore: false,
    label: "",
  },
);

const emit = defineEmits<{
  (event: "select", id: string | number): void;
  (event: "load-more"): void;
}>();

const scrollEl = ref<HTMLElement | null>(null);

useInfiniteScroll(
  scrollEl,
  () => emit("load-more"),
  {
    distance: 80,
    canLoadMore: () => Boolean(props.hasMore) && !props.loadingMore,
  },
);
</script>

<template>
  <aside class="flex w-72 shrink-0 flex-col border-r border-default">
    <div
      v-if="label"
      class="border-b border-default px-4 py-2.5 text-xs font-medium uppercase tracking-wide text-muted"
    >
      {{ label }}
    </div>
    <div
      ref="scrollEl"
      class="master-scroll min-h-0 flex-1 overflow-y-auto py-1"
    >
      <button
        v-for="entry in items"
        :key="entry.id"
        type="button"
        class="block w-full border-l-4 px-4 py-2.5 text-left transition-colors"
        :class="entry.id === selectedId
          ? 'border-l-primary bg-primary/10'
          : 'border-l-transparent hover:bg-elevated'"
        @click="emit('select', entry.id)"
      >
        <span class="block truncate text-sm font-semibold text-highlighted">
          {{ entry.title }}
        </span>
        <span
          v-if="entry.subtitle"
          class="block truncate text-xs text-muted"
        >
          {{ entry.subtitle }}
        </span>
      </button>

      <div
        v-if="loadingMore"
        class="flex items-center justify-center gap-2 py-3 text-xs text-muted"
      >
        <UIcon name="i-lucide-loader-circle" class="size-4 animate-spin" />
        <span>Загрузка...</span>
      </div>
    </div>
  </aside>
</template>

<style scoped>
/* Тонкий скроллбар — стандартный слишком широк для узкого списка. */
.master-scroll {
  scrollbar-width: thin;
  scrollbar-color: var(--ui-border-accented) transparent;
}

.master-scroll::-webkit-scrollbar {
  width: 6px;
}

.master-scroll::-webkit-scrollbar-thumb {
  background-color: var(--ui-border-accented);
  border-radius: 9999px;
}

.master-scroll::-webkit-scrollbar-track {
  background: transparent;
}
</style>
