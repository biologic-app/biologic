<script setup lang="ts">
import {
  computed,
  h,
  nextTick,
  onMounted,
  provide,
  reactive,
  ref,
  resolveComponent,
  watch,
} from "vue";
import type { DropdownMenuItem, TableColumn as NuxtTableColumn, TableRow } from "@nuxt/ui";
import type { CrudModuleConfig } from "@/pages/CrudModulePage.vue";
import type { FormField } from "@/shared/types/form";
import type { TableFilters } from "@/shared/types/table";
import CrudFormModal from "@/shared/ui/CrudFormModal.vue";
import CrudTableEmptyState from "@/shared/ui/CrudTableEmptyState.vue";
import CrudTableLoadingRows from "@/shared/ui/CrudTableLoadingRows.vue";
import CrudTableShell from "@/shared/ui/CrudTableShell.vue";
import CrudFilterModal from "@/shared/ui/CrudFilterModal.vue";
import ConfirmDialog from "@/shared/ui/ConfirmDialog.vue";
import RowContextMenu from "@/shared/ui/RowContextMenu.vue";
import {
  borderedCrudTableUi,
  createSkeletonRows,
  isSkeletonRow,
  renderSkeletonCell,
} from "@/shared/ui/table";

import { useCrudDialog } from "@/shared/composables/useCrudDialog";
import { useOptimistic } from "@/shared/composables/useOptimistic";
import { usePermission } from "@/shared/composables/usePermission";
import {
  TABLE_PRESETS_KEY,
  useServerTable,
} from "@/shared/composables/useServerTable";
import {
  apiCreateRequest,
  apiReadListRequest,
  apiRequest,
  apiUpdateRequest,
  loadReferenceOptions,
} from "@/shared/api/client.api";
import { formatDateTime } from "@/shared/utils/format";
import { getValueByPath } from "@/shared/utils/object";

type CrudRow = {
  id: string | number;
  [key: string]: unknown;
};

const props = defineProps<{
  config: CrudModuleConfig;
  requestParams?: Record<string, string>;
  search?: string;
  refreshToken?: number;
  resetToken?: number;
}>();

const UButton = resolveComponent("UButton");
const UBadge = resolveComponent("UBadge");
const UCheckbox = resolveComponent("UCheckbox");

const toast = useToast();
const { can } = usePermission();
const filterModalOpen = ref(false);

const confirmDialog = ref<{ open: boolean; title: string; description: string; onConfirm: () => void }>({
  open: false,
  title: "",
  description: "",
  onConfirm: () => {},
});

const deleting = ref(false);
const pendingUndo = ref<Array<{ item: CrudRow; timeout: ReturnType<typeof setTimeout> }>>([]);

function undoDelete(undoEntry: { item: CrudRow; timeout: ReturnType<typeof setTimeout> }) {
  clearTimeout(undoEntry.timeout);
  pendingUndo.value = pendingUndo.value.filter((e) => e !== undoEntry);
  table.data.value = [undoEntry.item, ...table.data.value];
  apiCreateRequest<CrudRow>(props.config.endpoint, {
    method: "POST",
    body: { ...props.requestParams, ...undoEntry.item },
  }).catch(() => {
    table.data.value = table.data.value.filter((row) => row.id !== undoEntry.item.id);
    toast.add({
      title: "Не удалось восстановить запись",
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  });
}

const table = useServerTable<CrudRow>(
  (params) =>
    apiReadListRequest<CrudRow>(props.config.endpoint, {
      method: "GET",
      params: {
        ...params,
        ...props.requestParams,
        include: props.config.include,
      },
    }),
  {
    mode: "infinite",
    presetKey: props.config.presetKey,
    filters: props.config.initialFilters,
    initialPageSize: props.config.pageSize ?? 20,
  },
);

provide(TABLE_PRESETS_KEY, {
  presets: table.presets,
  savePreset: table.savePreset,
  applyPreset: table.applyPreset,
  deletePreset: table.deletePreset,
});

const dialog = useCrudDialog<CrudRow>(props.config.resource);
const optimistic = useOptimistic<CrudRow>();
const saving = ref(false);
const formFields = ref<FormField[]>(
  props.config.fields.map((field) => ({ ...field })),
);
const columnVisibility = ref<Record<string, boolean>>({});
const rowSelection = ref<Record<string, boolean>>({});
const contextRow = ref<CrudRow | null>(null);
const contextMenuOpen = ref(false);
const contextMenuPosition = ref({ x: 0, y: 0 });
const skeletonRows = createSkeletonRows<CrudRow>(17);
const filters = reactive<TableFilters>(
  JSON.parse(JSON.stringify(props.config.initialFilters)),
);

const tableRows = computed(() =>
  table.loading.value ? skeletonRows : table.data.value,
);

const syncFilters = () => {
  Object.entries(table.filters.value).forEach(([key, value]) => {
    filters[key] = { ...value };
  });
};

syncFilters();

watch(
  () => table.filters.value,
  () => {
    syncFilters();
  },
  { deep: true },
);

watch(
  () => props.search,
  (value) => {
    filters.global.value = value || "";
    applyFilters(true);
  },
);

watch(
  () => props.refreshToken,
  () => {
    table.refresh();
  },
);

watch(
  () => props.resetToken,
  () => {
    resetFilters();
  },
);

onMounted(async () => {
  await Promise.all([
    table.fetch(),
    Promise.all(
      props.config.fields
        .filter(
          (field) => field.type === "select" && field.options === undefined,
        )
        .map(async (field) => {
          const endpoint = field.source;
          if (!endpoint) {
            return;
          }
          const options = await loadReferenceOptions(endpoint).catch(() => []);
          formFields.value = formFields.value.map((item) =>
            item.key === field.key ? { ...item, options } : item,
          );
        }),
    ),
  ]);
});

const uiColumns = computed(() => {
  const selectColumn: NuxtTableColumn<CrudRow> = {
    id: "select",
    enableSorting: false,
    enableHiding: false,
    header: ({ table: currentTable }) =>
      h(UCheckbox, {
        modelValue: currentTable.getIsSomePageRowsSelected()
          ? "indeterminate"
          : currentTable.getIsAllPageRowsSelected(),
        "onUpdate:modelValue": (value: boolean | "indeterminate") =>
          currentTable.toggleAllPageRowsSelected(!!value),
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


  const actionColumn = { id: "actions", header: "Действия", meta: { class: { td: "w-auto min-w-[56px] text-right" } } };

  return [
    selectColumn,
    ...props.config.columns.map((column, columnIndex) => ({
      id: column.field,
      accessorKey: column.field,
      header: () =>
        h(UButton, {
          color: "neutral",
          variant: "ghost",
          label: column.header,
          disabled: !column.sortable,
          icon:
            table.sorting.value.field !== column.field
              ? "i-lucide-arrow-up-down"
              : table.sorting.value.order === 1
                ? "i-lucide-arrow-up-narrow-wide"
                : "i-lucide-arrow-down-wide-narrow",
          class: column.sortable
            ? "-mx-2.5"
            : "pointer-events-none -mx-2.5 opacity-100",
          onClick: () => column.sortable && table.setSort(column.field),
        }),
      cell: ({ row }: { row: TableRow<CrudRow> }) => {
        const rowItem = row.original as CrudRow;
        if (isSkeletonRow(rowItem)) {
          return renderSkeletonCell(column.field, columnIndex);
        }

        if (column.body) {
          return column.body(rowItem);
        }

        const value = getValueByPath(rowItem, column.field);

        if (typeof value === "boolean") {
          return h(
            UBadge,
            {
              color: "neutral",
              variant: "subtle",
            },
            () => (value ? "Да" : "Нет"),
          );
        }

        if (typeof value === "string" && /(at|date)$/i.test(column.field)) {
          return formatDateTime(value);
        }

        return value ?? "-";
      },
      meta: {
        class: {
          th: column.width ? `w-[${column.width}]` : undefined,
        },
      },
    })),
    actionColumn,
  ] as NuxtTableColumn<CrudRow>[];
});

const applyFilters = (debounceGlobal = false) => {
  table.updateFilters(JSON.parse(JSON.stringify(filters)), debounceGlobal);
};

const resetFilters = () => {
  Object.keys(props.config.initialFilters).forEach((key) => {
    filters[key] = { ...props.config.initialFilters[key] };
  });
  applyFilters();
};

const errorMessage = (error: unknown) =>
  error instanceof Error ? error.message : "Попробуйте ещё раз";

const onSave = async (payload: Record<string, unknown>) => {
  const requestPayload = {
    ...props.requestParams,
    ...payload,
  };

  saving.value = true;
  try {
    if (dialog.mode.value === "create") {
      const response = await apiCreateRequest<CrudRow>(props.config.endpoint, {
        method: "POST",
        body: requestPayload,
      });
      table.data.value = [response.data, ...table.data.value];
    } else if (dialog.selected.value?.id) {
      const optimisticRow = { ...dialog.selected.value, ...requestPayload };
      const rollback = optimistic.updateItem(table.data, optimisticRow);
      try {
        const response = await apiUpdateRequest<CrudRow>(
          `${props.config.endpoint}/${dialog.selected.value.id}`,
          {
            method: "PATCH",
            body: requestPayload,
          },
        );
        table.data.value = table.data.value.map((item) =>
          item.id === dialog.selected.value?.id ? response.data : item,
        );
      } catch (error: unknown) {
        rollback();
        throw error;
      }
    }

    dialog.close();
  } catch (error: unknown) {
    toast.add({
      title: "Не удалось сохранить",
      description: errorMessage(error),
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    saving.value = false;
  }
};

const confirmDelete = async (row: CrudRow) => {
  confirmDialog.value = {
    open: true,
    title: "Удалить запись",
    description: `Вы уверены, что хотите удалить запись ${row.id}? Это действие нельзя отменить.`,
    async onConfirm() {
      deleting.value = true;
      const deletedRow = { ...table.data.value.find((r) => r.id === row.id) || row };
      const rollback = optimistic.removeItem(table.data, row.id);

      try {
        await apiRequest(`${props.config.endpoint}/${row.id}`, {
          method: "DELETE",
        });
        const timeout = setTimeout(() => {
          pendingUndo.value = pendingUndo.value.filter((e) => e.item.id !== row.id);
        }, 8000);
        const undoEntry = { item: deletedRow, timeout };
        pendingUndo.value.push(undoEntry);
        toast.add({
          title: "Запись удалена",
          description: "Запись будет удалена безвозвратно через 8 секунд.",
          color: "success",
          icon: "i-lucide-circle-check",
          actions: [
            {
              label: "Отменить",
              icon: "i-lucide-undo-2",
              onClick: () => undoDelete(undoEntry),
            },
          ],
          duration: 8000,
        });
      } catch (error: unknown) {
        rollback();
        toast.add({
          title: "Не удалось удалить",
          description: errorMessage(error),
          color: "error",
          icon: "i-lucide-circle-alert",
        });
      } finally {
        deleting.value = false;
        confirmDialog.value.open = false;
      }
    },
  };
};

const selectedRows = computed(() =>
  Object.keys(rowSelection.value)
    .filter((key) => rowSelection.value[key])
    .map((key) => table.data.value[Number(key)])
    .filter(Boolean),
);

const selectedCount = computed(() => selectedRows.value.length);

const deleteSelected = async () => {
  if (!selectedRows.value.length) {
    return;
  }

  confirmDialog.value = {
    open: true,
    title: "Удалить выбранные записи",
    description: `Вы уверены, что хотите удалить ${selectedRows.value.length} записей? Это действие нельзя отменить.`,
    async onConfirm() {
      deleting.value = true;

      const rows = [...selectedRows.value];
      const ids = rows.map((row) => row.id);
      const previous = [...table.data.value];
      table.data.value = table.data.value.filter((row) => !ids.includes(row.id));

      try {
        await Promise.all(
          rows.map((row) =>
            apiRequest(`${props.config.endpoint}/${row.id}`, { method: "DELETE" }),
          ),
        );
        rowSelection.value = {};
        toast.add({
          title: "Записи удалены",
          color: "success",
          icon: "i-lucide-circle-check",
        });
      } catch (error: unknown) {
        table.data.value = previous;
        toast.add({
          title: "Не удалось удалить выбранные записи",
          description: errorMessage(error),
          color: "error",
          icon: "i-lucide-circle-alert",
        });
      } finally {
        deleting.value = false;
        confirmDialog.value.open = false;
      }
    },
  };
};

const getRowActionItems = (row: CrudRow): DropdownMenuItem[] => [
  { label: "Просмотр", icon: "i-lucide-eye", onSelect: () => dialog.openView(row) },
  { label: "Редактировать", icon: "i-lucide-pencil", onSelect: () => dialog.openEdit(row) },
  { label: "Удалить", icon: "i-lucide-trash-2", color: "error", onSelect: () => confirmDelete(row) },
];

const handleRowSelect = (_event: Event, row: { original: CrudRow }) => {
  if (isSkeletonRow(row.original)) {
    return;
  }

  dialog.openView(row.original);
};

const contextMenuItems = computed(() =>
  contextRow.value ? getRowActionItems(contextRow.value) : [],
);

const handleRowContextmenu = async (event: Event, row: { original: CrudRow }) => {
  event.preventDefault();
  if (isSkeletonRow(row.original)) {
    return;
  }

  const mouseEvent = event as MouseEvent;
  contextRow.value = row.original;
  contextMenuOpen.value = false;
  contextMenuPosition.value = { x: mouseEvent.clientX, y: mouseEvent.clientY };
  await nextTick();
  contextMenuOpen.value = true;
};

const getColumnKey = (column: NuxtTableColumn<CrudRow>) => {
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
    uiColumns.value.filter((column) => {
      const key = getColumnKey(column);
      return !key || columnVisibility.value[key] !== false;
    }).length,
  ),
);

const createDisabled = computed(() => !can(props.config.resource, "create"));
const activeFilterCount = computed(() =>
  Object.entries(filters).filter(([key, filter]) => {
    if (key === "global") {
      return false;
    }

    const value = filter.value;
    if (Array.isArray(value)) {
      return value.some((item) => item !== null && item !== "");
    }

    return value !== null && value !== undefined && value !== "";
  }).length,
);

const columnMenuItems = computed(() =>
  [
    ...props.config.columns.map((column) => ({
      label: column.header,
      type: "checkbox" as const,
      checked: columnVisibility.value[column.field] !== false,
      onUpdateChecked(checked: boolean) {
        columnVisibility.value = {
          ...columnVisibility.value,
          [column.field]: checked,
        };
      },
      onSelect(event?: Event) {
        event?.preventDefault();
      },
    })),
    {
      label: "Действия",
      type: "checkbox" as const,
      checked: columnVisibility.value.actions !== false,
      onUpdateChecked(checked: boolean) {
        columnVisibility.value = {
          ...columnVisibility.value,
          actions: checked,
        };
      },
      onSelect(event?: Event) {
        event?.preventDefault();
      },
    },
  ],
);

const openCreate = () => {
  if (!createDisabled.value) {
    dialog.openCreate();
  }
};

defineExpose({
  openCreate,
  createDisabled,
  activeFilterCount,
  selectedCount,
  deleteSelected,
  columnMenuItems,
  filterModalOpen,
});
</script>

<template>
  <CrudFilterModal
    v-model:open="filterModalOpen"
    :active-count="activeFilterCount"
    @apply="applyFilters()"
    @reset="resetFilters()"
  >
    <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      <div
        v-for="column in config.columns.filter((column) => column.filter)"
        :key="column.field"
        class="grid gap-2"
      >
        <label class="text-sm font-medium text-toned">
          {{ column.header }}
        </label>

        <div
          v-if="column.filter?.type === 'dateRange'"
          class="grid gap-2 sm:grid-cols-2"
        >
          <UInput
            :model-value="filters[column.field].value?.[0] || ''"
            type="date"
            @update:model-value="
              filters[column.field].value = [
                $event || null,
                filters[column.field].value?.[1] || null,
              ]
            "
          />
          <UInput
            :model-value="filters[column.field].value?.[1] || ''"
            type="date"
            @update:model-value="
              filters[column.field].value = [
                filters[column.field].value?.[0] || null,
                $event || null,
              ]
            "
          />
        </div>

        <USelectMenu
          v-else-if="column.filter?.type === 'multiSelect'"
          :model-value="filters[column.field].value || []"
          :items="column.filter?.options || []"
          value-key="value"
          label-key="label"
          multiple
          clear
          @update:model-value="
            filters[column.field].value = $event
          "
        />

        <UInput
          v-else
          v-model="filters[column.field].value"
          :placeholder="column.filter?.placeholder || column.header"
        />
      </div>
    </div>
  </CrudFilterModal>

  <CrudTableShell
    mode="infinite"
    :total="table.total.value"
    :loading-more="table.loadingMore.value"
    :has-more="!table.loading.value && table.hasMore.value"
    @load-more="table.loadMore()"
  >
    <template #table>
      <RowContextMenu
        v-model:open="contextMenuOpen"
        :items="contextMenuItems"
        :x="contextMenuPosition.x"
        :y="contextMenuPosition.y"
      />
      <UTable
        v-model:column-visibility="columnVisibility"
        v-model:row-selection="rowSelection"
        :data="tableRows"
        :columns="uiColumns"
        :loading="false"
        :on-select="handleRowSelect"
        :on-contextmenu="handleRowContextmenu"
        sticky
        :ui="borderedCrudTableUi"
      >
        <template #body-bottom>
          <tr v-if="!table.loading.value && table.loadingMore.value" class="border-b border-default">
            <td :colspan="visibleColumnCount" class="border-r border-b border-default p-0">
              <CrudTableLoadingRows compact :columns="visibleColumnCount" />
            </td>
          </tr>
          <tr v-else-if="!table.loading.value && !table.hasMore.value && table.total.value > 0" class="bg-default">
            <td :colspan="visibleColumnCount" class="border-r border-b border-default px-6 py-3 text-center text-xs text-dimmed">
              Всего записей: {{ table.total.value }}
            </td>
          </tr>
        </template>
        <template #actions-cell="{ row }">
          <USkeleton v-if="isSkeletonRow(row.original)" class="ml-auto h-4 w-8" />
          <UDropdownMenu
            v-else
            :content="{ align: 'end' }"
            :items="getRowActionItems(row.original)"
          >
            <UButton icon="i-lucide-ellipsis-vertical" color="neutral" variant="ghost" size="sm" />
          </UDropdownMenu>
        </template>
        <template #empty>
          <CrudTableEmptyState
            :title="activeFilterCount ? 'Ничего не найдено' : 'Нет записей'"
            :description="activeFilterCount
              ? `В справочнике «${config.title}» нет записей, соответствующих фильтрам.`
              : `В справочнике «${config.title}» пока нет данных. Создайте первую запись.`"
            :filtered="activeFilterCount > 0"
            :error="table.error.value"
            error-description="Не удалось загрузить данные. Проверьте подключение или повторите попытку позже."
            @clear-filters="resetFilters"
            @retry="table.refresh()"
          />
        </template>
      </UTable>
    </template>
  </CrudTableShell>

  <CrudFormModal
    v-model:open="dialog.visible.value"
    :title="
      dialog.mode.value === 'create'
        ? `Создать: ${config.title}`
        : dialog.mode.value === 'edit'
          ? `Редактировать: ${config.title}`
          : `Просмотр: ${config.title}`
    "
    :fields="formFields"
    :item="dialog.selected.value"
    :mode="dialog.mode.value"
    :read-only="dialog.readOnly.value"
    :loading="saving"
    @save="onSave"
  />

  <ConfirmDialog
    v-model:open="confirmDialog.open"
    :title="confirmDialog.title"
    :description="confirmDialog.description"
    :loading="deleting"
    confirm-color="error"
    confirm-label="Удалить"
    confirm-icon="i-lucide-trash-2"
    @confirm="confirmDialog.onConfirm"
  />
</template>
