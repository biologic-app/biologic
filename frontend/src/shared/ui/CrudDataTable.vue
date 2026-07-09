<script setup lang="ts" generic="TRow extends object">
import { computed, h, resolveComponent, useSlots } from "vue";
import type { TableColumn, TableRow } from "@nuxt/ui";
import CrudTableLoadingRows from "@/shared/ui/CrudTableLoadingRows.vue";
import CrudTableShell from "@/shared/ui/CrudTableShell.vue";
import SelectionActionBar from "@/shared/ui/SelectionActionBar.vue";
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
    canDelete?: boolean;
    tableUi?: Record<string, unknown>;
    highlightId?: string | null;
  }>(),
  {
    loading: false,
    loadingMore: false,
    hasMore: false,
    selectable: false,
    canDelete: true,
    tableUi: undefined,
    highlightId: null,
  },
);

const emit = defineEmits<{
  (event: "loadMore"): void;
  (event: "rowSelect", nativeEvent: Event, row: { original: TRow }): void;
  (event: "rowContextmenu", nativeEvent: Event, row: { original: TRow }): void;
  (event: "deleteSelected"): void;
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
const slots = useSlots();
const reservedSlotNames = new Set([
  "before-table",
  "actions-cell",
  "empty",
  "selection-actions",
]);

const selectedRows = computed(() =>
  props.data.filter(
    (row) => rowSelection.value[String((row as Record<string, unknown>).id)],
  ),
);
const selectedCount = computed(() => selectedRows.value.length);
const clearSelection = () => {
  rowSelection.value = {};
};

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

// Подсветка недавно затронутой строки (например, только что созданный/дозаполненный
// черновик). Мягкий фон затухает автоматически, когда родитель сбрасывает highlightId.
const tableMeta = computed(() => ({
  class: {
    tr: (row: TableRow<TRow>) =>
      props.highlightId
      && String((row.original as Record<string, unknown>).id) === props.highlightId
        ? "bg-primary/15"
        : "",
  },
}));

const isInteractiveTarget = (event: Event) => {
  const target = event.target;
  if (!(target instanceof Element)) {
    return false;
  }

  return Boolean(
    target.closest(
      "button, a, input, textarea, select, [role='checkbox']",
    ),
  );
};

const handleRowSelect = (event: Event, row: TableRow<TRow>) => {
  if (props.selectable) {
    if (isSkeletonRow(row.original) || isInteractiveTarget(event)) {
      return;
    }

    row.toggleSelected(!row.getIsSelected());
    return;
  }

  emit("rowSelect", event, row);
};

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

const forwardedSlotNames = computed(() =>
  Object.keys(slots).filter((name) => !reservedSlotNames.has(name)),
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
        :get-row-id="(row: TRow) => String((row as Record<string, unknown>).id)"
        :data="data"
        :columns="tableColumns"
        :loading="loading"
        :on-select="handleRowSelect"
        :on-contextmenu="(event: Event, row: { original: TRow }) =>
          emit('rowContextmenu', event, row)"
        empty=" "
        sticky
        :meta="tableMeta"
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

        <template
          v-for="name in forwardedSlotNames"
          #[name]="slotProps"
        >
          <slot
            :name="name"
            v-bind="slotProps"
          />
        </template>

        <template #empty>
          <slot name="empty" />
        </template>
      </UTable>
    </template>

    <template v-if="selectable" #overlay>
      <SelectionActionBar
        :count="selectedCount"
        :can-delete="canDelete"
        @clear="clearSelection"
        @delete="emit('deleteSelected')"
      >
        <template #default="{ actionClass }">
          <slot
            name="selection-actions"
            :rows="selectedRows"
            :count="selectedCount"
            :clear="clearSelection"
            :action-class="actionClass"
          />
        </template>
      </SelectionActionBar>
    </template>
  </CrudTableShell>
</template>
