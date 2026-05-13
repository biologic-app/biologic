<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from "vue";

const props = withDefaults(
  defineProps<{
    total: number;
    page?: number;
    pageSize?: number;
    pageSizeItems?: number[];
    mode?: "paginated" | "infinite";
    loadingMore?: boolean;
    hasMore?: boolean;
  }>(),
  {
    mode: "paginated",
    page: undefined,
    pageSize: undefined,
    pageSizeItems: undefined,
    loadingMore: false,
    hasMore: false,
  },
);

const emit = defineEmits<{
  (event: "update:page", value: number): void;
  (event: "update:pageSize", value: number): void;
  (event: "loadMore"): void;
}>();

const sectionRef = ref<HTMLElement | null>(null);
let io: IntersectionObserver | null = null;
let mo: MutationObserver | null = null;

function findTbody(): HTMLTableSectionElement | null {
  // Search from section down — UTable renders table with tbody even inside scroll wrapper
  return sectionRef.value?.querySelector("tbody") ?? document.querySelector("tbody");
}

function findScrollRoot(): HTMLElement | null {
  return sectionRef.value?.querySelector(".crud-table-scroll") ?? null;
}

function observeLastRow() {
  io?.disconnect();
  const tbody = findTbody();
  if (!tbody) return;
  const rows = tbody.querySelectorAll("tr");
  const lastRow = rows[rows.length - 1];
  if (!lastRow) return;

  io = new IntersectionObserver(
    (entries) => {
      if (entries[0]?.isIntersecting && props.hasMore && !props.loadingMore) {
        emit("loadMore");
      }
    },
    { root: findScrollRoot(), rootMargin: "240px 0px" },
  );
  io.observe(lastRow);
}

onMounted(() => {
  nextTick(() => {
    observeLastRow();
    const tbody = findTbody();
    if (tbody) {
      mo = new MutationObserver(() => observeLastRow());
      mo.observe(tbody, { childList: true });
    }
  });
});

onUnmounted(() => {
  io?.disconnect();
  mo?.disconnect();
});
</script>

<template>
  <section ref="sectionRef" class="flex h-full min-h-0 min-w-0 flex-1 flex-col">
    <div class="min-h-0 flex-1 overflow-hidden">
      <slot name="table" />
    </div>

    <div v-if="mode === 'paginated'" class="flex shrink-0 flex-col gap-3 py-4 pr-4 sm:flex-row sm:items-center sm:justify-between">
      <div class="flex items-center gap-3 text-sm text-toned">
        <span>Всего: {{ total }}</span>
        <USelectMenu
          :model-value="pageSize ?? 20"
          :items="pageSizeItems || [20, 30, 50, 100]"
          class="w-24"
          @update:model-value="emit('update:pageSize', Number($event))"
        />
      </div>
      <UPagination
        :page="page ?? 1"
        :items-per-page="pageSize ?? 20"
        :total="total"
        show-edges
        @update:page="emit('update:page', $event)"
      />
    </div>
  </section>
</template>
