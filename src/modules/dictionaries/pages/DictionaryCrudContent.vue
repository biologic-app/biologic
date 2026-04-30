<script setup lang="ts">
import {
  computed,
  h,
  onMounted,
  provide,
  reactive,
  ref,
  resolveComponent,
  watch,
} from "vue";
import type { TableColumn as NuxtTableColumn, TableRow } from "@nuxt/ui";
import type { CrudModuleConfig } from "@/pages/CrudModulePage.vue";
import type { FormField } from "@/shared/types/form";
import type { TableFilters } from "@/shared/types/table";
import CrudFormModal from "@/shared/ui/CrudFormModal.vue";
import CrudTableEmptyState from "@/shared/ui/CrudTableEmptyState.vue";
import CrudTableShell from "@/shared/ui/CrudTableShell.vue";
import { borderedCrudTableUi } from "@/shared/ui/table";
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
  filtersOpen?: boolean;
  refreshToken?: number;
  resetToken?: number;
}>();

const UButton = resolveComponent("UButton");
const UBadge = resolveComponent("UBadge");
const UCheckbox = resolveComponent("UCheckbox");

const toast = useToast();
const { can } = usePermission();
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
const pageSizeItems = [20, 30, 50, 100];
const filters = reactive<TableFilters>(
  JSON.parse(JSON.stringify(props.config.initialFilters)),
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
    cell: ({ row }) =>
      h(UCheckbox, {
        modelValue: row.getIsSelected(),
        "onUpdate:modelValue": (value: boolean | "indeterminate") =>
          row.toggleSelected(!!value),
        ariaLabel: "Выбрать строку",
      }),
  };

  const actionColumn: NuxtTableColumn<CrudRow> = {
    id: "actions",
    enableHiding: false,
    header: "Действия",
    cell: ({ row }) => {
      const item = row.original as CrudRow;

      const viewButton = h(UButton, {
        color: "neutral",
        variant: "ghost",
        icon: "i-lucide-eye",
        onClick: () => dialog.openView(item),
      });

      const editButton = h(UButton, {
        color: "neutral",
        variant: "ghost",
        icon: can(props.config.resource, "edit")
          ? "i-lucide-pencil"
          : "i-lucide-lock",
        title: can(props.config.resource, "edit")
          ? "Редактировать"
          : "Нет прав",
        disabled: !can(props.config.resource, "edit"),
        onClick: () => dialog.openEdit(item),
      });

      const deleteButton = h(UButton, {
        color: "error",
        variant: "ghost",
        icon: can(props.config.resource, "delete")
          ? "i-lucide-trash-2"
          : "i-lucide-lock",
        title: can(props.config.resource, "delete") ? "Удалить" : "Нет прав",
        disabled: !can(props.config.resource, "delete"),
        onClick: () => confirmDelete(item),
      });

      return h("div", { class: "flex items-center justify-end gap-1" }, [
        viewButton,
        editButton,
        deleteButton,
      ]);
    },
    meta: { class: { td: "w-[140px] text-right" } },
  };

  return [
    selectColumn,
    ...props.config.columns.map((column) => ({
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
  if (!window.confirm(`Удалить запись ${row.id}?`)) {
    return;
  }

  const rollback = optimistic.removeItem(table.data, row.id);

  try {
    await apiRequest(`${props.config.endpoint}/${row.id}`, {
      method: "DELETE",
    });
  } catch (error: unknown) {
    rollback();
    toast.add({
      title: "Не удалось удалить",
      description: errorMessage(error),
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  }
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

  if (!window.confirm(`Удалить выбранные записи (${selectedRows.value.length})?`)) {
    return;
  }

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
  } catch (error: unknown) {
    table.data.value = previous;
    toast.add({
      title: "Не удалось удалить выбранные записи",
      description: errorMessage(error),
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  }
};

const paginationPage = computed({
  get: () => table.pagination.value.page + 1,
  set: (value: number) => table.setPage(value - 1),
});

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
});
</script>

<template>
  <CrudTableShell
    :filters-open="props.filtersOpen"
    :total="table.total.value"
    :page="paginationPage"
    :page-size="table.pagination.value.size"
    :page-size-items="pageSizeItems"
    @update:page="paginationPage = $event"
    @update:page-size="table.setPageSize($event)"
  >
    <template #filters>
      <div class="grid gap-3 border-t border-default pt-3 md:grid-cols-2 xl:grid-cols-3">
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
                ];
                applyFilters();
              "
            />
            <UInput
              :model-value="filters[column.field].value?.[1] || ''"
              type="date"
              @update:model-value="
                filters[column.field].value = [
                  filters[column.field].value?.[0] || null,
                  $event || null,
                ];
                applyFilters();
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
              filters[column.field].value = $event;
              applyFilters();
            "
          />

          <UInput
            v-else
            v-model="filters[column.field].value"
            :placeholder="column.filter?.placeholder || column.header"
            @update:model-value="applyFilters()"
          />
        </div>
      </div>
    </template>

    <template #table>
      <UTable
        v-model:column-visibility="columnVisibility"
        v-model:row-selection="rowSelection"
        :data="table.data.value"
        :columns="uiColumns"
        :loading="table.loading.value"
        sticky
        class="h-full"
        :ui="borderedCrudTableUi"
      >
        <template #empty>
          <CrudTableEmptyState
            title="Нет записей"
            :description="`В справочнике «${config.title}» пока нет данных.`"
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
</template>
