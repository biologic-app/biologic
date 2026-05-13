<script setup lang="ts" generic="TRow extends object">
import { computed, h, resolveComponent } from "vue";
import type { TableColumn } from "@nuxt/ui";
import CrudTableLoadingRows from "@/shared/ui/CrudTableLoadingRows.vue";
import CrudTableShell from "@/shared/ui/CrudTableShell.vue";
import {
  borderedCrudTableUi,
  isSkeletonRow,
  renderSkeletonCell,
} from "@/shared/ui/table";

const props = withDefaults(
  defineProps<{
    data: TRow[];
    columns: TableColumn<TRow>[];
    total: number;
    loading?: boolean;
    loadingMore?: boolean;
    hasMore?: boolean;
    selectable?: boolean;
    tableUi?: Record<string, unknown>;
  }>(),
  {
    loading: false,
    loadingMore: false,
    hasMore: false,
    selectable: false,
    tableUi: undefined,
  },
);

const emit = defineEmits<{
  (event: "loadMore"): void;
  (event: "rowSelect", nativeEvent: Event, row: { original: TRow }): void;
  (event: "rowContextmenu", nativeEvent: Event, row: { original: TRow }): void;
}>();

const columnVisibility = defineModel<Record<string, boolean>>(
  "columnVisibility",
  { default: () => ({}) },
);
const rowSelection = defineModel<Record<string, boolean>>(
  "rowSelection",
  { default: () => ({}) },
);

const UCheckbox = resolveComponent("UCheckbox");

const selectColumn: TableColumn<TRow> = {
  id: "select",
  enableSorting: false,
  enableHiding: false,
  header: ({ table }) =>
    h(UCheckbox, {
      modelValue: table.getIsSomePageRowsSelected()
        ? "indeterminate"
        : table.getIsAllPageRowsSelected(),
      "onUpdate:modelValue": (value: boolean | "indeterminate") =>
        table.toggleAllPageRowsSelected(!!value),
      ariaLabel: "Выбрать все строки",
    }),
  cell: ({ row }) => {
    if (isSkeletonRow(row.original)) {
      return renderSkeletonCell("select");
    }

    return h(UCheckbox, {
      modelValue: row.getIsSelected(),
      "onUpdate:modelValue": (value: boolean | "indeterminate") =>
        row.toggleSelected(!!value),
      ariaLabel: "Выбрать строку",
    });
  },
};

const tableColumns = computed(() =>
  props.selectable ? [selectColumn, ...props.columns] : props.columns,
);

const tableUiConfig = computed(() => props.tableUi ?? borderedCrudTableUi);

const getColumnKey = (column: TableColumn<TRow>) => {
  if ("id" in column && typeof column.id === "string") {
    return column.id;
  }
  if ("accessorKey" in column && typeof column.accessorKey === "string") {
    return column.accessorKey;
  }
  return "";
};

const visibleColumnCount = computed(() =>
  Math.max(
    1,
    tableColumns.value.filter((column) => {
      const key = getColumnKey(column);
      return !key || columnVisibility.value[key] !== false;
    }).length,
  ),
);
</script>

<template>
  <CrudTableShell
    mode="infinite"
    :total="total"
    :loading-more="loadingMore"
    :has-more="!loading && hasMore"
    @load-more="emit('loadMore')"
  >
    <template #table>
      <slot name="before-table" />
      <UTable
        v-model:column-visibility="columnVisibility"
        v-model:row-selection="rowSelection"
        :data="data"
        :columns="tableColumns"
        :loading="loading"
        :on-select="(event: Event, row: { original: TRow }) =>
          emit('rowSelect', event, row)"
        :on-contextmenu="(event: Event, row: { original: TRow }) =>
          emit('rowContextmenu', event, row)"
        sticky
        :ui="tableUiConfig"
      >
        <template #body-bottom>
          <tr
            v-if="!loading && loadingMore"
            class="border-b border-default"
          >
            <td
              :colspan="visibleColumnCount"
              class="border-r border-b border-default p-0"
            >
              <CrudTableLoadingRows compact :columns="visibleColumnCount" />
            </td>
          </tr>
          <tr
            v-else-if="!loading && !hasMore && total > 0"
            class="bg-default"
          >
            <td
              :colspan="visibleColumnCount"
              class="border-r border-b border-default px-6 py-3 text-center text-xs text-dimmed"
            >
              Всего записей: {{ total }}
            </td>
          </tr>
        </template>

        <template #actions-cell="{ row }">
          <slot name="actions-cell" :row="row" />
        </template>

        <template #empty>
          <slot name="empty" />
        </template>
      </UTable>
    </template>
  </CrudTableShell>
</template>
