<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    columns?: number;
    columnKeys?: string[];
    rows?: number;
    compact?: boolean;
  }>(),
  {
    columns: 6,
    rows: 20,
    compact: false,
  },
);

const skeletonColumns = computed(() =>
  props.columnKeys?.length
    ? props.columnKeys
    : Array.from({ length: props.columns }, (_, index) => `column-${index}`),
);

const gridTemplateColumns = computed(() =>
  skeletonColumns.value
    .map((key) => {
      if (key === "select") return "3rem";
      if (key === "actions") return "5rem";
      return "minmax(8rem, 1fr)";
    })
    .join(" "),
);

const getSkeletonWidth = (key: string, index: number) => {
  if (key === "select") return "1.25rem";
  if (key === "actions") return "2rem";
  return index % 3 === 0 ? "70%" : index % 3 === 1 ? "86%" : "58%";
};
</script>

<template>
  <div v-if="compact" class="flex items-center gap-3 px-6 py-3 text-sm text-muted">
    <UIcon name="i-lucide-loader-circle" class="size-4 animate-spin" />
    <span>Подгружаем данные...</span>
    <USkeleton class="h-3 w-32" />
  </div>

  <div v-else class="min-w-full">
    <div
      v-for="row in rows"
      :key="row"
      class="grid border-b border-default last:border-b-0"
      :style="{ gridTemplateColumns }"
    >
      <div
        v-for="(column, columnIndex) in skeletonColumns"
        :key="column"
        class="flex h-10 items-center border-r border-default px-6 last:border-r-0"
      >
        <USkeleton
          class="h-4"
          :style="{ width: getSkeletonWidth(column, columnIndex) }"
        />
      </div>
    </div>
  </div>
</template>
