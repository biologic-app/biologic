<script setup lang="ts">
defineProps<{
  filtersOpen?: boolean;
  total: number;
  page: number;
  pageSize: number;
  pageSizeItems?: number[];
  showFilters?: boolean;
}>();

const emit = defineEmits<{
  (event: "update:page", value: number): void;
  (event: "update:pageSize", value: number): void;
}>();
</script>

<template>
  <section class="flex h-full min-h-0 min-w-0 flex-1 flex-col">
    <div v-if="showFilters !== false" class="shrink-0">
      <UCollapsible
        :open="filtersOpen"
      >
        <template #content>
          <slot name="filters" />
        </template>
      </UCollapsible>
    </div>

    <div class="min-h-0 flex-1 overflow-auto">
      <slot name="table" />
    </div>

    <div class="flex shrink-0 flex-col gap-3 py-4 pr-4 sm:flex-row sm:items-center sm:justify-between">
      <div class="flex items-center gap-3 text-sm text-toned">
        <span>Всего: {{ total }}</span>
        <USelectMenu
          :model-value="pageSize"
          :items="pageSizeItems || [20, 30, 50, 100]"
          class="w-24"
          @update:model-value="emit('update:pageSize', Number($event))"
        />
      </div>
      <UPagination
        :page="page"
        :items-per-page="pageSize"
        :total="total"
        show-edges
        @update:page="emit('update:page', $event)"
      />
    </div>
  </section>
</template>
