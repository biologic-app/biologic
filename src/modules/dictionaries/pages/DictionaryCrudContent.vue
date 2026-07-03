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
import type { CrudModuleConfig, CrudRow } from '@/shared/types/crud';
import type { FormField } from "@/shared/types/form";
import { workflowCommands } from "@/shared/domain/workflow-commands";
import type { WorkflowCommand, WorkflowCommandKey } from "@/shared/domain/workflow-commands";
import type { TableColumn, TableFilters } from "@/shared/types/table";
import CrudFormModal from "@/shared/ui/CrudFormModal.vue";
import CrudDataTable from "@/shared/ui/CrudDataTable.vue";
import CrudTableEmptyState from "@/shared/ui/CrudTableEmptyState.vue";
import CrudFilterModal from "@/shared/ui/CrudFilterModal.vue";
import CrudDateRangeFilter from "@/shared/ui/CrudDateRangeFilter.vue";
import ConfirmDialog from "@/shared/ui/ConfirmDialog.vue";
import RowContextMenu from "@/shared/ui/RowContextMenu.vue";
import BusinessEntityDetailModal from "@/shared/ui/BusinessEntityDetailModal.vue";
import DictionaryCrudDetailModal from "@/shared/ui/DictionaryCrudDetailModal.vue";
import ProtocolPreviewModal from "@/shared/ui/ProtocolPreviewModal.vue";
import type { DetailListItem } from "@/shared/ui/EntityDetailModalShell.vue";
import {
  filterSelectOverlayUi,
  getFilterSelectModelValue,
  normalizeFilterSelectValue,
} from "@/shared/ui/filter-select";
import {
  createSkeletonRows,
  isSkeletonRow,
  renderSkeletonCell,
} from "@/shared/ui/table";

import { useCrudDialog } from "@/shared/composables/useCrudDialog";
import { useOptimistic } from "@/shared/composables/useOptimistic";
import { usePermission } from "@/shared/composables/usePermission";
import { useRelatedEntities } from "@/shared/composables/useRelatedEntities";
import { useTableColumnVisibility } from "@/shared/composables/useTableSettings";
import { useAuth } from "@/modules/auth/composables/useAuth";
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
import { crudModules, getCrudModuleFilterFields } from "@/shared/config/crud-modules";
import { clone } from "@/shared/utils/clone";
import { formatDateTime } from "@/shared/utils/format";
import { getValueByPath } from "@/shared/utils/object";
import { getStatusBadgeColor as resolveStatusBadgeColor, resolveStatusCode } from "@/shared/domain/status";
import { getEntityRule, type EntityDetailKind } from "@/shared/domain/entity-rules";

type DetailKind = EntityDetailKind;
type BadgeColor = ReturnType<typeof resolveStatusBadgeColor>;
type ReferenceValue = string | number | boolean | null;
type ReferenceOption = { label: string; value: ReferenceValue };

const props = withDefaults(
  defineProps<{
    config: CrudModuleConfig;
    requestParams?: Record<string, string>;
    search?: string;
    refreshToken?: number;
    resetToken?: number;
    selectable?: boolean;
  }>(),
  {
    requestParams: undefined,
    search: undefined,
    refreshToken: undefined,
    resetToken: undefined,
    selectable: true,
  },
);

const UButton = resolveComponent("UButton");
const UBadge = resolveComponent("UBadge");

const toast = useToast();
const auth = useAuth();
const { can } = usePermission();
const filterModalOpen = defineModel<boolean>("filterOpen", { default: false });
const tableSettingsKey = `table-settings:dictionaries:${props.config.presetKey}:${JSON.stringify(props.requestParams ?? {})}`;
const sortableFields = computed(() =>
  props.config.columns
    .filter((column) => column.sortable)
    .map((column) => column.field),
);

const confirmDialog = ref<{ open: boolean; title: string; description: string; onConfirm: () => void }>({
  open: false,
  title: "",
  description: "",
  onConfirm: () => {},
});

const deleting = ref(false);
const commandSaving = ref(false);
const commandDialogOpen = ref(false);
const activeCommand = ref<WorkflowCommand | null>(null);
const commandRows = ref<CrudRow[]>([]);
const commandFields = ref<FormField[]>([]);
const protocolSaving = ref(false);
const protocolDialogOpen = ref(false);
const protocolFields = ref<FormField[]>([]);
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
    settingsKey: tableSettingsKey,
    filters: props.config.initialFilters,
    initialPageSize: props.config.pageSize ?? 100,
    sortableFields: sortableFields.value,
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
const detailOpen = ref(false);
const detailItem = ref<CrudRow | null>(null);
const detailConfig = ref<CrudModuleConfig>(props.config);
// Правила сущности (удаление/карточка/создание) — из данных, без preset-веток.
const entityRule = computed(() => getEntityRule(props.config.presetKey));
const detailKind = ref<DetailKind | null>(entityRule.value.detailKind ?? null);
const formFields = ref<FormField[]>(
  props.config.fields.map((field) => ({ ...field })),
);
const referenceOptions = ref<Record<string, ReferenceOption[]>>({});
const formReferenceOptionsLoaded = ref(false);
const formReferenceOptionsLoading = ref(false);
const filterReferenceOptionsLoaded = ref(false);
const filterReferenceOptionsLoading = ref(false);
const columnVisibility = useTableColumnVisibility(tableSettingsKey, { actions: false });
const rowSelection = ref<Record<string, boolean>>({});
const contextRow = ref<CrudRow | null>(null);
const contextMenuOpen = ref(false);
const contextMenuPosition = ref({ x: 0, y: 0 });
const previewRow = ref<CrudRow | null>(null);
const previewOpen = ref(false);
const { relatedRows: previewSamples, loadRelatedRows: loadPreviewSamples } = useRelatedEntities({
  currentItem: () => previewRow.value,
  businessKind: () => "protocols",
});

async function openPreview(row: CrudRow) {
  previewRow.value = row;
  await loadPreviewSamples(true);
  previewOpen.value = true;
}
const skeletonRows = createSkeletonRows<CrudRow>(17);
const filters = reactive<TableFilters>(
  clone(props.config.initialFilters),
);

const filterFields = computed(() =>
  getCrudModuleFilterFields(props.config),
);

const cloneFilterMeta = (value: TableFilters[string]) =>
  clone(value);

const createFilterMeta = (field: TableColumn) => {
  if (field.filter?.type === "dateRange") {
    return { value: [null, null], matchMode: "between" };
  }
  return { value: "", matchMode: "contains" };
};

const getFilterOptions = (field: TableColumn) =>
  referenceOptions.value[field.field] ?? field.filter?.options ?? [];

const isFilterOptionsLoading = (field: TableColumn) =>
  filterReferenceOptionsLoading.value
  && field.filter?.type === "select"
  && field.filter.options === undefined
  && Boolean(field.filter.source)
  && referenceOptions.value[field.field] === undefined;

const ensureFilterEntries = () => {
  filterFields.value.forEach((field) => {
    if (!filters[field.field]) {
      filters[field.field] = createFilterMeta(field);
    }
  });
};

const tableRows = computed(() =>
  table.loading.value ? skeletonRows : table.data.value,
);

const syncFilters = () => {
  Object.entries(table.filters.value).forEach(([key, value]) => {
    filters[key] = cloneFilterMeta(value);
  });
  ensureFilterEntries();
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

watch(
  filterModalOpen,
  (open) => {
    if (open) {
      void loadFilterReferenceOptions();
    }
  },
);

onMounted(async () => {
  await table.fetch();
});

async function loadFormReferenceOptions() {
  if (formReferenceOptionsLoaded.value || formReferenceOptionsLoading.value) {
    return;
  }

  formReferenceOptionsLoading.value = true;
  try {
    await Promise.all(
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
          referenceOptions.value = {
            ...referenceOptions.value,
            [field.key]: options as ReferenceOption[],
          };
          formFields.value = formFields.value.map((item) =>
            item.key === field.key ? { ...item, options } : item,
          );
        }),
    );
    formReferenceOptionsLoaded.value = true;
  } finally {
    formReferenceOptionsLoading.value = false;
  }
}

async function loadFilterReferenceOptions() {
  if (filterReferenceOptionsLoaded.value || filterReferenceOptionsLoading.value) {
    return;
  }

  filterReferenceOptionsLoading.value = true;
  try {
    await Promise.all(
      filterFields.value
        .filter(
          (field) =>
            field.filter?.type === "select"
            && field.filter.options === undefined
            && field.filter.source,
        )
        .map(async (field) => {
          const endpoint = field.filter?.source;
          if (!endpoint) {
            return;
          }
          const options = await loadReferenceOptions(endpoint).catch(() => []);
          referenceOptions.value = {
            ...referenceOptions.value,
            [field.field]: options as ReferenceOption[],
          };
        }),
    );
    filterReferenceOptionsLoaded.value = true;
  } finally {
    filterReferenceOptionsLoading.value = false;
  }
}

const formatShortEntityCode = (value: unknown) => {
  if (typeof value !== "string" && typeof value !== "number") {
    return "";
  }

  const text = String(value);
  const uuidPrefix = text.match(/^[0-9a-f]{8}/i)?.[0];
  return (uuidPrefix ?? text.slice(0, 8)).toUpperCase();
};

const getReferenceLabel = (fieldKey: string, value: unknown) => {
  if (value === null || value === undefined || value === "") {
    return "";
  }

  return referenceOptions.value[fieldKey]?.find((option) => String(option.value) === String(value))?.label ?? "";
};

const getRelationIdField = (columnField: string) => {
  const [relationKey, relationField] = columnField.split(".");
  if (!relationKey || !relationField) {
    return columnField.endsWith("_id") ? columnField : "";
  }

  return `${relationKey}_id`;
};

const resolveReferenceCell = (row: CrudRow, columnField: string) => {
  const relationIdField = getRelationIdField(columnField);
  if (!relationIdField) {
    return "";
  }

  const idValue = getValueByPath(row, relationIdField);
  const label = getReferenceLabel(relationIdField, idValue);
  if (label) {
    return label;
  }

  const shortCode = formatShortEntityCode(idValue);
  return shortCode ? `Запись ${shortCode}` : "";
};

const getStringValue = (value: unknown) =>
  typeof value === "string" && value.trim() ? value.trim() : "";

const getStatusLabel = (row: CrudRow) => {
  const statusValue = getValueByPath(row, "status");
  const label =
    getStringValue(getValueByPath(row, "status.name"))
    || getStringValue(getValueByPath(row, "status_name"))
    || getStringValue(statusValue)
    || resolveReferenceCell(row, "status.name");

  return label || "-";
};

const normalizeStatusCode = (row: CrudRow) => {
  const rawCode = getValueByPath(row, "status.code");
  const value = String(rawCode || getStatusLabel(row)).trim().toLowerCase();
  return resolveStatusCode(value);
};

const getStatusBadgeColor = (row: CrudRow): BadgeColor =>
  resolveStatusBadgeColor(normalizeStatusCode(row));

// Левый master-список детальной модалки: текущие строки таблицы (тот же
// бесконечный скролл, что и в таблице — через table.loadMore).
const detailListItems = computed<DetailListItem[]>(() =>
  table.data.value.map((row) => ({
    id: row.id,
    title:
      getStringValue(getValueByPath(row, "name"))
      || getStringValue(getValueByPath(row, "full_name"))
      || getStringValue(getValueByPath(row, "code"))
      || `Запись ${formatShortEntityCode(row.id)}`,
    subtitle:
      getStringValue(getValueByPath(row, "code"))
      || getStatusLabel(row),
    color: getStatusBadgeColor(row),
  })),
);

const selectDetailRow = (id: string | number) => {
  const row = table.data.value.find((entry) => String(entry.id) === String(id));
  if (row) {
    detailItem.value = row;
  }
};


const getColumnId = (columnField: string) =>
  columnField === "status.name" ? "status" : columnField;

const isDeleteAllowed = (row: CrudRow) => {
  if (!can(props.config.resource, "delete")) {
    return false;
  }
  const allowed = entityRule.value.deletableStatuses;
  return allowed ? allowed.includes(normalizeStatusCode(row)) : true;
};

const deleteRestriction = computed(() => entityRule.value.deleteRestriction ?? "");

const getActorId = () => {
  if (auth.user?.id) {
    return auth.user.id;
  }

  toast.add({
    title: "Не удалось выполнить действие",
    description: "Текущий пользователь не определён.",
    color: "error",
    icon: "i-lucide-circle-alert",
  });
  return null;
};

const selectedRowsHaveStatus = (allowed: string[]) =>
  selectedRows.value.length > 0
  && selectedRows.value.every((row) => allowed.includes(normalizeStatusCode(row)));

const uiColumns = computed(() => {
  const actionColumn = { id: "actions", header: "Действия", meta: { class: { td: "w-auto min-w-[56px] text-right" } } };

  return [
    ...props.config.columns.map((column, columnIndex) => ({
      id: getColumnId(column.field),
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
        const referenceCell = value ?? resolveReferenceCell(rowItem, column.field);

        if (typeof referenceCell === "boolean") {
          return h(
            UBadge,
            {
              color: "neutral",
              variant: "subtle",
            },
            () => (referenceCell ? "Да" : "Нет"),
          );
        }

        if (typeof referenceCell === "string" && /(at|date)$/i.test(column.field)) {
          return formatDateTime(referenceCell);
        }

        return referenceCell === "" ? "-" : referenceCell ?? "-";
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
  table.updateFilters(clone(filters), debounceGlobal);
};

const resetFilters = () => {
  Object.keys(props.config.initialFilters).forEach((key) => {
    filters[key] = cloneFilterMeta(props.config.initialFilters[key]);
  });
  filterFields.value.forEach((field) => {
    if (!filters[field.field]) {
      filters[field.field] = createFilterMeta(field);
    }
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
  if (!isDeleteAllowed(row)) {
    toast.add({
      title: "Удаление недоступно",
      description: deleteRestriction.value,
      color: "warning",
      icon: "i-lucide-circle-alert",
    });
    return;
  }

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

const selectedRows = computed(() => {
  const ids = new Set(Object.keys(rowSelection.value).filter((k) => rowSelection.value[k]));
  return table.data.value.filter((row) => ids.has(String(row.id)));
});

const selectedCount = computed(() => selectedRows.value.length);
const canDeleteSelected = computed(() =>
  selectedRows.value.length > 0 && selectedRows.value.every(isDeleteAllowed),
);

const commandByKey = (key: WorkflowCommandKey) =>
  workflowCommands.find((command) => command.key === key);

const commandBelongsToPage = (command: WorkflowCommand) =>
  command.resource === props.config.presetKey;

const canRunCommandOnRow = (command: WorkflowCommand, row: CrudRow) =>
  commandBelongsToPage(command)
  && can(command.resource, command.action)
  && command.statuses.includes(normalizeStatusCode(row));

const canRunCommandOnSelection = (key: WorkflowCommandKey) => {
  const command = commandByKey(key);
  return Boolean(
    command
    && commandBelongsToPage(command)
    && can(command.resource, command.action)
    && selectedRowsHaveStatus(command.statuses),
  );
};

// Команды этой страницы — единый источник для кнопок массовых действий.
// Каждая кнопка рисуется по данным команды (label/color/icon), доступность
// считается через canRunCommandOnSelection — без 11 ручных computeds/обёрток.
const pageWorkflowCommands = computed(() =>
  workflowCommands.filter(commandBelongsToPage),
);

const commandInitialItem = computed(() => {
  if (!activeCommand.value) {
    return null;
  }

  const defaults: Record<string, unknown> = {};
  activeCommand.value.fields.forEach((field) => {
    if (field.type === "date" && field.required) {
      defaults[field.key] = new Date().toISOString();
      return;
    }
    defaults[field.key] = "";
  });
  return defaults;
});

const runWorkflowCommand = async (
  command: WorkflowCommand,
  rows: CrudRow[],
  payload: Record<string, unknown> = {},
) => {
  const actorId = getActorId();
  if (!actorId || !rows.length) {
    return;
  }

  commandSaving.value = true;
  try {
    await Promise.all(
      rows.map((row) =>
        apiRequest(command.endpoint(row), {
          method: "POST",
          body: command.body(actorId, payload),
        }),
      ),
    );
    rowSelection.value = {};
    commandDialogOpen.value = false;
    await table.refresh();
    toast.add({
      title: command.successTitle,
      color: "success",
      icon: "i-lucide-circle-check",
    });
  } catch (error: unknown) {
    toast.add({
      title: command.errorTitle,
      description: errorMessage(error),
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    commandSaving.value = false;
  }
};

const loadCommandFieldOptions = async (fields: FormField[]) => {
  const loadedFields = await Promise.all(
    fields.map(async (field) => {
      if (field.type !== "select" || field.options || !field.source) {
        return field;
      }

      const options = await loadReferenceOptions(field.source).catch(() => []);
      return { ...field, options };
    }),
  );
  commandFields.value = loadedFields;
};

const openWorkflowCommand = async (key: WorkflowCommandKey, rows: CrudRow[]) => {
  const command = commandByKey(key);
  const allowedRows = rows.filter((row) => command && canRunCommandOnRow(command, row));
  if (!command || !allowedRows.length) {
    toast.add({
      title: "Действие недоступно",
      description: "Проверьте статус выбранных записей и права доступа.",
      color: "warning",
      icon: "i-lucide-circle-alert",
    });
    return;
  }

  if (!command.fields.length) {
    await runWorkflowCommand(command, allowedRows);
    return;
  }

  activeCommand.value = command;
  commandRows.value = allowedRows;
  await loadCommandFieldOptions(command.fields);
  commandDialogOpen.value = true;
};

const saveWorkflowCommand = async (payload: Record<string, unknown>) => {
  if (!activeCommand.value) {
    return;
  }

  await runWorkflowCommand(activeCommand.value, commandRows.value, payload);
};

// Протокол связывает N образцов одним POST /protocols — это фан-ин, а не
// «одна и та же команда на каждую строку», поэтому не укладывается в
// workflowCommands (endpoint per-row) и живёт отдельным путём, доступным
// только со страницы образцов (см. docs/flows/registrator.flow.md §16).
const canCreateProtocolFromSelection = computed(() => {
  if (props.config.presetKey !== "samples" || !can("protocols", "create")) {
    return false;
  }
  const rows = selectedRows.value;
  if (!rows.length) {
    return false;
  }
  const directionId = getValueByPath(rows[0], "direction_id");
  return rows.every(
    (row) =>
      normalizeStatusCode(row) === "completed"
      && getValueByPath(row, "direction_id") === directionId
      && !getValueByPath(row, "protocol_id"),
  );
});

const openProtocolDialog = async () => {
  if (!canCreateProtocolFromSelection.value) {
    toast.add({
      title: "Создание протокола недоступно",
      description: "Выберите завершённые образцы одного направления.",
      color: "warning",
      icon: "i-lucide-circle-alert",
    });
    return;
  }

  const fields = crudModules.protocols.fields.filter((field) =>
    ["protocol_type_id", "conclusion_id", "copies"].includes(field.key),
  );
  await loadCommandFieldOptions(fields);
  protocolFields.value = commandFields.value;
  protocolDialogOpen.value = true;
};

const saveProtocolCommand = async (payload: Record<string, unknown>) => {
  const actorId = getActorId();
  if (!actorId || !canCreateProtocolFromSelection.value) {
    return;
  }

  protocolSaving.value = true;
  try {
    await apiRequest("/protocols", {
      method: "POST",
      body: {
        actor_id: actorId,
        sample_ids: selectedRows.value.map((row) => row.id),
        protocol_type_id: payload.protocol_type_id || null,
        conclusion_id: payload.conclusion_id || null,
        copies: payload.copies ? Number(payload.copies) : null,
      },
    });
    rowSelection.value = {};
    protocolDialogOpen.value = false;
    await table.refresh();
    toast.add({
      title: "Протокол создан",
      color: "success",
      icon: "i-lucide-circle-check",
    });
  } catch (error: unknown) {
    toast.add({
      title: "Не удалось создать протокол",
      description: errorMessage(error),
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    protocolSaving.value = false;
  }
};

const deleteSelected = async () => {
  if (!selectedRows.value.length) {
    return;
  }

  if (!canDeleteSelected.value) {
    toast.add({
      title: "Удаление недоступно",
      description: deleteRestriction.value,
      color: "warning",
      icon: "i-lucide-circle-alert",
    });
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

const runSelectedCommand = (key: WorkflowCommandKey) =>
  openWorkflowCommand(key, selectedRows.value);

const resolveDetailKind = (config: CrudModuleConfig): DetailKind | null =>
  getEntityRule(config.presetKey).detailKind ?? null;

const openDetail = (row: CrudRow, config: CrudModuleConfig = props.config) => {
  detailItem.value = row;
  detailConfig.value = config;
  detailKind.value = resolveDetailKind(config);
  detailOpen.value = true;
};

const onDetailSaved = (row: CrudRow) => {
  if (detailConfig.value.presetKey !== props.config.presetKey) {
    return;
  }

  table.data.value = table.data.value.map((item) =>
    item.id === row.id ? { ...item, ...row } : item,
  );
};

const openRelatedDetail = (payload: { kind: DetailKind; item: CrudRow }) => {
  const config = crudModules[payload.kind];
  if (config) {
    openDetail(payload.item, config);
  }
};

const getRowWorkflowActionItems = (row: CrudRow): DropdownMenuItem[] =>
  workflowCommands
    .filter(commandBelongsToPage)
    .map((command) => ({
      label: `${command.label} · ${command.title}`,
      icon: command.icon,
      disabled: !canRunCommandOnRow(command, row),
      ...(command.color === "error" ? { color: "error" as const } : {}),
      onSelect: () => openWorkflowCommand(command.key, [row]),
    }));

const getRowActionItems = (row: CrudRow): DropdownMenuItem[] => {
  const workflowItems = getRowWorkflowActionItems(row);
  return [
    { label: "Просмотр", icon: "i-lucide-eye", onSelect: () => openDetail(row) },
    ...(props.config.presetKey === "protocols"
      ? [{ label: "Предпросмотр", icon: "i-lucide-file-search", onSelect: () => openPreview(row) }]
      : []),
    {
      label: "Редактировать",
      icon: can(props.config.resource, "edit") ? "i-lucide-pencil" : "i-lucide-lock",
      disabled: !can(props.config.resource, "edit"),
      onSelect: () => openEdit(row),
    },
    ...workflowItems,
    {
      label: "Удалить",
      icon: "i-lucide-trash-2",
      color: "error",
      disabled: !isDeleteAllowed(row),
      onSelect: () => confirmDelete(row),
    },
  ];
};

const handleRowSelect = (_event: Event, row: { original: CrudRow }) => {
  if (isSkeletonRow(row.original)) {
    return;
  }

  openDetail(row.original);
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

const createDisabled = computed(() =>
  Boolean(entityRule.value.createDisabled) || !can(props.config.resource, "create"),
);
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
      checked: columnVisibility.value[getColumnId(column.field)] !== false,
      onUpdateChecked(checked: boolean) {
        columnVisibility.value = {
          ...columnVisibility.value,
          [getColumnId(column.field)]: checked,
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
    void loadFormReferenceOptions();
  }
};

const openEdit = (row: CrudRow) => {
  dialog.openEdit(row);
  void loadFormReferenceOptions();
};

const clearSelection = () => {
  rowSelection.value = {};
};

defineExpose({
  openCreate,
  createDisabled,
  activeFilterCount,
  columnMenuItems,
  filterModalOpen,
  clearSelection,
  // Используется страницей справочников (только массовое удаление).
  selectedCount,
  deleteSelected,
});
</script>

<template>
  <CrudFilterModal
    v-model:open="filterModalOpen"
    :active-count="activeFilterCount"
    @apply="applyFilters()"
    @reset="resetFilters()"
  >
    <div class="grid gap-3 md:grid-cols-2">
      <div
        v-for="filterField in filterFields"
        :key="filterField.field"
        class="grid gap-2"
      >
        <label class="text-sm font-medium text-toned">
          {{ filterField.header }}
        </label>

        <CrudDateRangeFilter
          v-if="filterField.filter?.type === 'dateRange'"
          v-model="filters[filterField.field].value"
        />

        <USelectMenu
          v-else-if="filterField.filter?.type === 'select' || filterField.filter?.type === 'multiSelect'"
          :model-value="getFilterSelectModelValue(filters[filterField.field].value)"
          :items="getFilterOptions(filterField)"
          value-key="value"
          label-key="label"
          :placeholder="filterField.filter?.placeholder || filterField.header"
          :portal="false"
          :ui="filterSelectOverlayUi"
          :loading="isFilterOptionsLoading(filterField)"
          clear
          @update:model-value="
            filters[filterField.field].value = normalizeFilterSelectValue($event)
          "
        >
          <template #empty>
            <div
              v-if="isFilterOptionsLoading(filterField)"
              class="flex items-center gap-2 py-1 text-sm text-muted"
            >
              <UIcon name="i-lucide-loader-circle" class="size-4 animate-spin" />
              <span>Загрузка...</span>
            </div>
          </template>
        </USelectMenu>

        <UInput
          v-else
          v-model="filters[filterField.field].value"
          :placeholder="filterField.filter?.placeholder || filterField.header"
        />
      </div>
    </div>
  </CrudFilterModal>

  <CrudDataTable
    v-model:column-visibility="columnVisibility"
    v-model:row-selection="rowSelection"
    :data="tableRows"
    :columns="uiColumns"
    :total="table.total.value"
    :loading="table.loading.value"
    :loading-more="table.loadingMore.value"
    :has-more="table.hasMore.value"
    :selectable="selectable"
    :can-delete="canDeleteSelected"
    @load-more="table.loadMore()"
    @row-select="handleRowSelect"
    @row-contextmenu="handleRowContextmenu"
    @delete-selected="deleteSelected"
  >
    <template #before-table>
      <RowContextMenu
        v-model:open="contextMenuOpen"
        :items="contextMenuItems"
        :x="contextMenuPosition.x"
        :y="contextMenuPosition.y"
      />
    </template>
    <template #actions-cell="{ row }">
      <USkeleton v-if="isSkeletonRow(row.original)" class="ml-auto h-4 w-8" />
      <UDropdownMenu
        v-else
        :content="{ align: 'end' }"
        :items="getRowActionItems(row.original)"
      >
        <UButton
          icon="i-lucide-ellipsis-vertical"
          color="neutral"
          variant="ghost"
          size="sm"
        />
      </UDropdownMenu>
    </template>
    <template #status-cell="{ row }">
      <USkeleton v-if="isSkeletonRow(row.original)" class="h-5 w-24" />
      <UBadge
        v-else
        :color="getStatusBadgeColor(row.original)"
        variant="subtle"
        :label="getStatusLabel(row.original)"
      />
    </template>
    <template #selection-actions="{ actionClass }">
      <UButton
        v-for="command in pageWorkflowCommands"
        :key="command.key"
        :label="command.selection.label"
        :icon="command.icon"
        :color="command.selection.color"
        variant="ghost"
        size="sm"
        :disabled="!canRunCommandOnSelection(command.key)"
        :class="actionClass"
        @click="runSelectedCommand(command.key)"
      />
      <UButton
        v-if="config.presetKey === 'samples' && can('protocols', 'create')"
        label="Создать протокол"
        icon="i-lucide-file-check-2"
        color="primary"
        variant="ghost"
        size="sm"
        data-testid="create-protocol-from-selection"
        :disabled="!canCreateProtocolFromSelection"
        :class="actionClass"
        @click="openProtocolDialog()"
      />
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
  </CrudDataTable>

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

  <CrudFormModal
    v-model:open="commandDialogOpen"
    :title="activeCommand?.title || 'Действие'"
    :fields="commandFields"
    :item="commandInitialItem"
    mode="create"
    :loading="commandSaving"
    @save="saveWorkflowCommand"
  />

  <CrudFormModal
    v-model:open="protocolDialogOpen"
    :title="`Создать протокол (${selectedCount} образцов)`"
    :fields="protocolFields"
    :item="{}"
    mode="create"
    :loading="protocolSaving"
    @save="saveProtocolCommand"
  />

  <BusinessEntityDetailModal
    v-if="detailKind"
    v-model:open="detailOpen"
    :config="detailConfig"
    :item="detailItem"
    :business-kind="detailKind"
    :list-items="detailListItems"
    :list-has-more="table.hasMore.value"
    :list-loading-more="table.loadingMore.value"
    @saved="onDetailSaved"
    @open-related="openRelatedDetail"
    @select="selectDetailRow"
    @list-load-more="table.loadMore()"
  />

  <DictionaryCrudDetailModal
    v-else
    v-model:open="detailOpen"
    :config="detailConfig"
    :item="detailItem"
    :list-items="detailListItems"
    :list-has-more="table.hasMore.value"
    :list-loading-more="table.loadingMore.value"
    @saved="onDetailSaved"
    @select="selectDetailRow"
    @list-load-more="table.loadMore()"
  />

  <ProtocolPreviewModal
    v-if="config.presetKey === 'protocols'"
    v-model:open="previewOpen"
    :protocol="previewRow"
    :samples="previewSamples"
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
