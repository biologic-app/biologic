<script setup lang="ts">
// Страница «Данные» — экспорт/импорт всей базы. Дамп лежит файлом в файловой
// системе сервера, в БД хранится только путь (таблица database_backups), поэтому
// таблица ниже — это реестр файлов, а не сами данные.
import { computed, h, nextTick, onMounted, onUnmounted, ref, resolveComponent, watch } from "vue";
import { useI18n } from "vue-i18n";
import type { DropdownMenuItem, TableColumn } from "@nuxt/ui";
import ConfirmDialog from "@/shared/ui/ConfirmDialog.vue";
import NotificationsBellButton from "@/shared/ui/NotificationsBellButton.vue";
import BackupHealthGrid from "@/modules/database/components/BackupHealthGrid.vue";
import CrudDataTable from "@/shared/ui/CrudDataTable.vue";
import CrudTableEmptyState from "@/shared/ui/CrudTableEmptyState.vue";
import CrudFilterControls from "@/shared/ui/CrudFilterControls.vue";
import CrudFilterModal from "@/shared/ui/CrudFilterModal.vue";
import CrudSearchControl from "@/shared/ui/CrudSearchControl.vue";
import RowContextMenu from "@/shared/ui/RowContextMenu.vue";
import { createSkeletonRows, isSkeletonRow } from "@/shared/ui/table";
import { useTableColumnVisibility } from "@/shared/composables/useTableSettings";
import {
  createBackup,
  deleteBackup,
  downloadBackup,
  fetchBackups,
  fetchDatabaseStatus,
  restoreBackup,
  uploadBackup,
} from "@/modules/database/api/database.api";
import type { BackupOrigin, BackupStatus, DatabaseBackup, DatabaseStatus } from "@/modules/database/types";
import { formatDateTime } from "@/shared/utils/format";

const { t } = useI18n();
const toast = useToast();

const status = ref<DatabaseStatus | null>(null);
const backups = ref<DatabaseBackup[]>([]);
const loading = ref(false);
const loadError = ref(false);
const creating = ref(false);
const uploading = ref(false);
const restoring = ref(false);
const deleting = ref(false);

const uploadOpen = ref(false);
const dragging = ref(false);
const selectedFile = ref<File | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);

const restoreTarget = ref<DatabaseBackup | null>(null);
const deleteTarget = ref<DatabaseBackup | null>(null);

const rowSelection = ref<Record<string, boolean>>({});
const contextRow = ref<DatabaseBackup | null>(null);
const contextMenuOpen = ref(false);
const contextMenuPosition = ref({ x: 0, y: 0 });
const bulkDeleteOpen = ref(false);
const bulkDeleting = ref(false);

const searchQuery = ref("");
const statusFilter = ref<BackupStatus | "">("");
const originFilter = ref<BackupOrigin | "">("");
const filterModalOpen = ref(false);
const columnVisibility = useTableColumnVisibility("table-settings:data-operations:v1");

type SortField = "filename" | "createdAt" | "status" | "sizeBytes" | "durationMs";
const sortField = ref<SortField>("createdAt");
const sortOrder = ref<1 | -1>(-1);

function setSort(field: SortField) {
  if (sortField.value === field) {
    sortOrder.value = sortOrder.value === 1 ? -1 : 1;
  } else {
    sortField.value = field;
    sortOrder.value = 1;
  }
}

const STATUS_COLOR: Record<BackupStatus, "success" | "error" | "info"> = {
  completed: "success",
  failed: "error",
  in_progress: "info",
};

function notifyError(title: string, error: unknown) {
  toast.add({
    title,
    description: error instanceof Error ? error.message : String(error),
    color: "error",
    icon: "i-lucide-circle-alert",
  });
}

async function copyRestoreError(text: string) {
  try {
    await navigator.clipboard.writeText(text);
    toast.add({
      title: t("dataOperations.toasts.copied"),
      color: "success",
      icon: "i-lucide-copy-check",
    });
  } catch (error) {
    notifyError(t("dataOperations.toasts.copyFailed"), error);
  }
}

function formatBytes(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "—";
  }
  const units = ["B", "KB", "MB", "GB", "TB"];
  let size = value;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024;
    unit += 1;
  }
  return `${size < 10 && unit > 0 ? size.toFixed(1) : Math.round(size)} ${units[unit]}`;
}

function formatDuration(ms: number | null): string {
  if (ms === null) {
    return "—";
  }
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`;
}

// Тикающие «сейчас» для живой длительности выполняющегося дампа — duration_ms
// сервер проставляет только по завершении, до этого момента считаем сами.
const now = ref(Date.now());

function displayDuration(backup: DatabaseBackup): string {
  if (backup.status === "in_progress") {
    return formatDuration(Math.max(0, now.value - new Date(backup.createdAt).getTime()));
  }
  return formatDuration(backup.durationMs);
}

// Пока дамп пишется на диск, его файл растёт — процент грубо оценивается
// относительно текущего размера базы (см. GET /database/status).
function progressPercent(backup: DatabaseBackup): number | undefined {
  const total = status.value?.sizeBytes;
  if (!total) {
    return undefined;
  }
  return Math.min(99, Math.round((backup.sizeBytes / total) * 100));
}

async function refresh() {
  loading.value = true;
  try {
    const [nextStatus, nextBackups] = await Promise.all([fetchDatabaseStatus(), fetchBackups()]);
    status.value = nextStatus;
    backups.value = nextBackups;
    loadError.value = false;
  } catch (error) {
    loadError.value = true;
    notifyError(t("dataOperations.toasts.loadFailed"), error);
  } finally {
    loading.value = false;
  }
}

// Тихий опрос без спиннера — идёт, пока хоть один дамп «Выполняется», не
// только запущенный из этой вкладки: дампы данных запускаются и снаружи.
async function silentRefresh() {
  try {
    const [nextStatus, nextBackups] = await Promise.all([fetchDatabaseStatus(), fetchBackups()]);
    status.value = nextStatus;
    backups.value = nextBackups;
  } catch {
    // Опрос идёт в фоне — сбой не должен спамить тостами, следующий тик сам поправит.
  }
}

const hasInProgress = computed(() => backups.value.some((backup) => backup.status === "in_progress"));
// `creating` covers the gap between clicking «Создать дамп» and the in_progress
// row actually landing in `backups` — the create POST only resolves once the
// whole dump is done, so without this the table would never learn to poll.
const shouldTrackProgress = computed(() => creating.value || hasInProgress.value);

let pollTimer: ReturnType<typeof setInterval> | null = null;
let clockTimer: ReturnType<typeof setInterval> | null = null;

watch(
  shouldTrackProgress,
  (active) => {
    if (active) {
      if (!pollTimer) {
        void silentRefresh();
        pollTimer = setInterval(silentRefresh, 1500);
      }
      if (!clockTimer) {
        clockTimer = setInterval(() => {
          now.value = Date.now();
        }, 1000);
      }
    } else {
      if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
      if (clockTimer) {
        clearInterval(clockTimer);
        clockTimer = null;
      }
    }
  },
  { immediate: true },
);

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer);
  }
  if (clockTimer) {
    clearInterval(clockTimer);
  }
});

onMounted(refresh);

async function onCreate() {
  creating.value = true;
  try {
    const backup = await createBackup();
    toast.add({
      title: t("dataOperations.toasts.created"),
      description: `${backup.filename} · ${formatBytes(backup.sizeBytes)}`,
      color: "success",
      icon: "i-lucide-database-backup",
    });
    await refresh();
  } catch (error) {
    notifyError(t("dataOperations.toasts.createFailed"), error);
  } finally {
    creating.value = false;
  }
}

function selectFile(file?: File | null) {
  if (file) {
    selectedFile.value = file;
  }
}

function onDrop(event: DragEvent) {
  dragging.value = false;
  selectFile(event.dataTransfer?.files?.[0]);
}

function openUpload() {
  selectedFile.value = null;
  uploadOpen.value = true;
}

async function onUpload() {
  if (!selectedFile.value) {
    return;
  }
  uploading.value = true;
  try {
    await uploadBackup(selectedFile.value);
    uploadOpen.value = false;
    selectedFile.value = null;
    toast.add({
      title: t("dataOperations.toasts.uploaded"),
      description: t("dataOperations.toasts.uploadedHint"),
      color: "success",
      icon: "i-lucide-upload",
    });
    await refresh();
  } catch (error) {
    notifyError(t("dataOperations.toasts.uploadFailed"), error);
  } finally {
    uploading.value = false;
  }
}

async function onDownload(backup: DatabaseBackup) {
  try {
    await downloadBackup(backup);
  } catch (error) {
    notifyError(t("dataOperations.toasts.downloadFailed"), error);
  }
}

async function onRestore() {
  const target = restoreTarget.value;
  if (!target) {
    return;
  }
  restoring.value = true;
  try {
    await restoreBackup(target.id);
    restoreTarget.value = null;
    toast.add({
      title: t("dataOperations.toasts.restored"),
      description: target.filename,
      color: "success",
      icon: "i-lucide-database-zap",
    });
    await refresh();
  } catch (error) {
    notifyError(t("dataOperations.toasts.restoreFailed"), error);
  } finally {
    restoring.value = false;
  }
}

async function onDelete() {
  const target = deleteTarget.value;
  if (!target) {
    return;
  }
  deleting.value = true;
  try {
    await deleteBackup(target.id);
    deleteTarget.value = null;
    toast.add({
      title: t("dataOperations.toasts.deleted"),
      description: target.filename,
      color: "success",
      icon: "i-lucide-trash-2",
    });
    await refresh();
  } catch (error) {
    notifyError(t("dataOperations.toasts.deleteFailed"), error);
  } finally {
    deleting.value = false;
  }
}

const selectedRows = computed(() => backups.value.filter((backup) => rowSelection.value[backup.id]));

async function onBulkDelete() {
  const rows = selectedRows.value;
  if (!rows.length) {
    return;
  }
  bulkDeleting.value = true;
  try {
    await Promise.all(rows.map((row) => deleteBackup(row.id)));
    rowSelection.value = {};
    bulkDeleteOpen.value = false;
    toast.add({
      title: t("dataOperations.toasts.deleted"),
      color: "success",
      icon: "i-lucide-trash-2",
    });
    await refresh();
  } catch (error) {
    notifyError(t("dataOperations.toasts.deleteFailed"), error);
  } finally {
    bulkDeleting.value = false;
  }
}

function getRowActionItems(backup: DatabaseBackup): DropdownMenuItem[] {
  return [
    {
      label: t("dataOperations.actions.download"),
      icon: "i-lucide-download",
      disabled: !backup.fileExists,
      onSelect: () => onDownload(backup),
    },
    {
      label: t("dataOperations.actions.restore"),
      icon: "i-lucide-database-zap",
      disabled: !backup.fileExists || backup.status !== "completed",
      onSelect: () => {
        restoreTarget.value = backup;
      },
    },
    {
      label: t("dataOperations.actions.delete"),
      icon: "i-lucide-trash-2",
      color: "error",
      onSelect: () => {
        deleteTarget.value = backup;
      },
    },
  ];
}

const contextMenuItems = computed(() => (contextRow.value ? getRowActionItems(contextRow.value) : []));

async function handleRowContextmenu(event: Event, row: { original: DatabaseBackup }) {
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
}

const summary = computed(() => [
  {
    key: "database",
    icon: "i-lucide-database",
    label: t("dataOperations.summary.database"),
    value: status.value?.name ?? "—",
    hint: status.value?.host ? `${status.value.host}:${status.value.port}` : "",
  },
  {
    key: "size",
    icon: "i-lucide-hard-drive",
    label: t("dataOperations.summary.size"),
    value: formatBytes(status.value?.sizeBytes),
    hint: t("dataOperations.summary.tables", { count: status.value?.tableCount ?? 0 }),
  },
  {
    key: "engine",
    icon: "i-lucide-settings-2",
    label: t("dataOperations.summary.engine"),
    value: t(`dataOperations.engine.${status.value?.engine ?? "sql"}`),
    hint: t(`dataOperations.engineHint.${status.value?.engine ?? "sql"}`),
  },
  {
    key: "storage",
    icon: "i-lucide-folder-open",
    label: t("dataOperations.summary.storage"),
    value: t("dataOperations.summary.backupCount", { count: status.value?.backupCount ?? 0 }),
    hint: status.value?.backupDir ?? "",
  },
]);

function sortableHeader(field: SortField, label: string) {
  const UButton = resolveComponent("UButton");
  return h(UButton, {
    color: "neutral",
    variant: "ghost",
    label,
    icon:
      sortField.value !== field
        ? "i-lucide-arrow-up-down"
        : sortOrder.value === 1
          ? "i-lucide-arrow-up-narrow-wide"
          : "i-lucide-arrow-down-wide-narrow",
    onClick: () => setSort(field),
  });
}

const columns = computed<TableColumn<DatabaseBackup>[]>(() => [
  { accessorKey: "filename", header: () => sortableHeader("filename", t("dataOperations.columns.file")) },
  { accessorKey: "createdAt", header: () => sortableHeader("createdAt", t("dataOperations.columns.date")) },
  { accessorKey: "status", header: () => sortableHeader("status", t("dataOperations.columns.status")) },
  { accessorKey: "restoreStatus", header: t("dataOperations.columns.restore") },
  { accessorKey: "origin", header: t("dataOperations.columns.origin") },
  { accessorKey: "sizeBytes", header: () => sortableHeader("sizeBytes", t("dataOperations.columns.size")) },
  { accessorKey: "durationMs", header: () => sortableHeader("durationMs", t("dataOperations.columns.duration")) },
  { id: "actions", header: t("dataOperations.columns.actions") },
]);

const columnLabels = computed<Record<string, string>>(() => ({
  filename: t("dataOperations.columns.file"),
  createdAt: t("dataOperations.columns.date"),
  status: t("dataOperations.columns.status"),
  restoreStatus: t("dataOperations.columns.restore"),
  origin: t("dataOperations.columns.origin"),
  sizeBytes: t("dataOperations.columns.size"),
  durationMs: t("dataOperations.columns.duration"),
  actions: t("dataOperations.columns.actions"),
}));

const columnMenuItems = computed(() =>
  Object.entries(columnLabels.value).map(([key, label]) => ({
    label,
    type: "checkbox" as const,
    checked: columnVisibility.value[key] !== false,
    onUpdateChecked(checked: boolean) {
      columnVisibility.value = { ...columnVisibility.value, [key]: checked };
    },
    onSelect(event?: Event) {
      event?.preventDefault();
    },
  })),
);

const statusFilterItems = computed(() => [
  { label: t("dataOperations.filters.allStatuses"), value: "" },
  { label: t("dataOperations.status.completed"), value: "completed" },
  { label: t("dataOperations.status.in_progress"), value: "in_progress" },
  { label: t("dataOperations.status.failed"), value: "failed" },
]);

const originFilterItems = computed(() => [
  { label: t("dataOperations.filters.allOrigins"), value: "" },
  { label: t("dataOperations.origin.export"), value: "export" },
  { label: t("dataOperations.origin.upload"), value: "upload" },
]);

const activeFilterCount = computed(() => (statusFilter.value ? 1 : 0) + (originFilter.value ? 1 : 0));

function resetFilters() {
  statusFilter.value = "";
  originFilter.value = "";
}

const isFiltered = computed(() => activeFilterCount.value > 0 || searchQuery.value.trim().length > 0);

function clearAllFilters() {
  resetFilters();
  searchQuery.value = "";
}

const visibleBackups = computed(() => {
  let list = backups.value;
  const query = searchQuery.value.trim().toLowerCase();
  if (query) {
    list = list.filter((backup) => backup.filename.toLowerCase().includes(query));
  }
  if (statusFilter.value) {
    list = list.filter((backup) => backup.status === statusFilter.value);
  }
  if (originFilter.value) {
    list = list.filter((backup) => backup.origin === originFilter.value);
  }

  const field = sortField.value;
  const order = sortOrder.value;
  return [...list].sort((a, b) => {
    const left = a[field];
    const right = b[field];
    if (left === right) {
      return 0;
    }
    if (left === null) {
      return 1;
    }
    if (right === null) {
      return -1;
    }
    if (typeof left === "number" && typeof right === "number") {
      return (left - right) * order;
    }
    return String(left).localeCompare(String(right)) * order;
  });
});

const skeletonRows = createSkeletonRows<DatabaseBackup>(5);
const tableRows = computed(() => (loading.value ? skeletonRows : visibleBackups.value));
</script>

<template>
  <UDashboardPanel id="data-operations" :ui="{ body: 'overflow-hidden min-h-0' }">
    <template #header>
      <UDashboardNavbar :title="t('nav.dataOperations')">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <UButton
            :label="t('dataOperations.actions.upload')"
            icon="i-lucide-upload"
            color="neutral"
            variant="subtle"
            data-testid="database-upload-open"
            @click="openUpload"
          />
          <UButton
            :label="t('dataOperations.actions.create')"
            icon="i-lucide-database-backup"
            :loading="creating"
            data-testid="database-create-backup"
            @click="onCreate"
          />
          <NotificationsBellButton />
        </template>
      </UDashboardNavbar>

      <UDashboardToolbar>
        <template #left>
          <div class="flex w-full flex-col gap-3 lg:flex-row lg:items-center">
            <CrudSearchControl
              v-model="searchQuery"
              :placeholder="t('dataOperations.searchPlaceholder')"
            />
            <CrudFilterControls
              :active-count="activeFilterCount"
              @open="filterModalOpen = true"
              @clear="resetFilters"
            />
          </div>
        </template>
        <template #right>
          <div class="flex flex-wrap items-center gap-2">
            <UTooltip :text="t('access.refreshData')">
              <UButton
                :label="t('common.update')"
                icon="i-lucide-refresh-cw"
                color="neutral"
                variant="subtle"
                :loading="loading"
                @click="refresh"
              />
            </UTooltip>
            <UDropdownMenu :items="columnMenuItems" :content="{ align: 'end' }">
              <UTooltip :text="t('access.tableColumns')">
                <UButton color="neutral" variant="subtle" trailing-icon="i-lucide-settings-2" />
              </UTooltip>
            </UDropdownMenu>
          </div>
        </template>
      </UDashboardToolbar>
    </template>

    <template #body>
      <CrudFilterModal
        v-model:open="filterModalOpen"
        :active-count="activeFilterCount"
        @reset="resetFilters"
      >
        <div class="grid gap-3 sm:grid-cols-2">
          <USelect v-model="statusFilter" :items="statusFilterItems" value-key="value" />
          <USelect v-model="originFilter" :items="originFilterItems" value-key="value" />
        </div>
      </CrudFilterModal>

      <div class="flex h-full min-h-0 flex-1 flex-col gap-4">
        <UAlert
          v-if="status && !status.reachable"
          class="shrink-0"
          color="error"
          variant="subtle"
          icon="i-lucide-database-zap"
          :title="t('dataOperations.unreachable')"
          :description="status.error ?? undefined"
        />

        <BackupHealthGrid class="shrink-0" :backups="backups" />

        <div class="grid shrink-0 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <div
            v-for="tile in summary"
            :key="tile.key"
            class="rounded-lg border border-default bg-elevated/40 p-4"
          >
            <div class="flex items-center gap-2 text-xs font-medium text-muted">
              <UIcon :name="tile.icon" class="size-4" />
              <span>{{ tile.label }}</span>
            </div>
            <p class="mt-2 truncate text-lg font-semibold text-highlighted">
              {{ tile.value }}
            </p>
            <p
              v-if="tile.hint"
              class="mt-0.5 truncate text-xs text-dimmed"
              :title="tile.hint"
            >
              {{ tile.hint }}
            </p>
          </div>
        </div>

        <CrudDataTable
          v-model:row-selection="rowSelection"
          v-model:column-visibility="columnVisibility"
          :data="tableRows"
          :columns="columns"
          :total="visibleBackups.length"
          :loading="loading"
          selectable
          @row-contextmenu="handleRowContextmenu"
          @delete-selected="bulkDeleteOpen = true"
        >
          <template #before-table>
            <RowContextMenu
              v-model:open="contextMenuOpen"
              :items="contextMenuItems"
              :x="contextMenuPosition.x"
              :y="contextMenuPosition.y"
            />
          </template>

          <template #filename-cell="{ row }">
            <div v-if="isSkeletonRow(row.original)" class="flex h-9 items-center">
              <div class="h-3.5 w-2/3 animate-pulse rounded-md bg-elevated" />
            </div>
            <p v-else class="truncate text-sm font-medium text-highlighted">
              {{ row.original.filename }}
            </p>
          </template>

          <template #createdAt-cell="{ row }">
            <div v-if="isSkeletonRow(row.original)" class="flex h-9 items-center">
              <div class="h-3.5 w-24 animate-pulse rounded-md bg-elevated" />
            </div>
            <span v-else class="text-sm text-muted">
              {{ formatDateTime(row.original.createdAt) }}
            </span>
          </template>

          <template #status-cell="{ row }">
            <div v-if="isSkeletonRow(row.original)" class="flex h-9 items-center">
              <div class="h-3.5 w-16 animate-pulse rounded-md bg-elevated" />
            </div>
            <div v-else class="flex flex-col items-start gap-1">
              <UBadge
                :color="STATUS_COLOR[row.original.status]"
                variant="subtle"
                :label="t(`dataOperations.status.${row.original.status}`)"
              />
              <div v-if="row.original.status === 'in_progress'" class="w-32">
                <UProgress :model-value="progressPercent(row.original)" size="xs" />
              </div>
              <span v-if="row.original.error" class="text-xs text-error">
                {{ row.original.error }}
              </span>
              <span v-else-if="!row.original.fileExists" class="text-xs text-warning">
                {{ t("dataOperations.fileMissing") }}
              </span>
            </div>
          </template>

          <template #restoreStatus-cell="{ row }">
            <div v-if="isSkeletonRow(row.original)" class="flex h-9 items-center">
              <div class="h-3.5 w-16 animate-pulse rounded-md bg-elevated" />
            </div>
            <span v-else-if="!row.original.restoreStatus" class="text-sm text-dimmed">—</span>
            <div v-else class="flex items-center gap-1">
              <UTooltip
                :text="t(
                  row.original.restoreStatus === 'failed'
                    ? 'dataOperations.restoreFailed'
                    : 'dataOperations.restoredAt',
                  {
                    name: row.original.restoredByName ?? t('dataOperations.unknownActor'),
                    date: formatDateTime(row.original.restoredAt),
                  },
                ) + (row.original.restoreStatus === 'failed' && row.original.restoreError
                  ? ` — ${row.original.restoreError}`
                  : '')"
                :ui="{ content: 'h-auto max-w-xs items-start whitespace-normal py-1.5', text: 'whitespace-normal' }"
              >
                <UBadge
                  :color="row.original.restoreStatus === 'failed' ? 'error' : 'success'"
                  variant="subtle"
                  :label="t(`dataOperations.restoreStatusLabel.${row.original.restoreStatus}`)"
                />
              </UTooltip>
              <UTooltip
                v-if="row.original.restoreStatus === 'failed' && row.original.restoreError"
                :text="t('dataOperations.actions.copyError')"
              >
                <UButton
                  icon="i-lucide-copy"
                  color="neutral"
                  variant="ghost"
                  size="xs"
                  :aria-label="t('dataOperations.actions.copyError')"
                  @click="copyRestoreError(row.original.restoreError)"
                />
              </UTooltip>
            </div>
          </template>

          <template #origin-cell="{ row }">
            <div v-if="isSkeletonRow(row.original)" class="flex h-9 items-center">
              <div class="h-3.5 w-5/6 animate-pulse rounded-md bg-elevated" />
            </div>
            <div v-else class="flex items-center gap-2">
              <UBadge
                color="neutral"
                variant="subtle"
                :label="t(`dataOperations.origin.${row.original.origin}`)"
              />
              <span class="text-xs text-dimmed">
                {{ t(`dataOperations.engine.${row.original.format}`) }}
              </span>
            </div>
          </template>

          <template #sizeBytes-cell="{ row }">
            <div v-if="isSkeletonRow(row.original)" class="flex h-9 items-center">
              <div class="h-3.5 w-12 animate-pulse rounded-md bg-elevated" />
            </div>
            <span v-else class="text-sm tabular-nums">{{ formatBytes(row.original.sizeBytes) }}</span>
          </template>

          <template #durationMs-cell="{ row }">
            <div v-if="isSkeletonRow(row.original)" class="flex h-9 items-center">
              <div class="h-3.5 w-10 animate-pulse rounded-md bg-elevated" />
            </div>
            <span v-else class="text-sm tabular-nums text-muted">
              {{ displayDuration(row.original) }}
            </span>
          </template>

          <template #actions-cell="{ row }">
            <USkeleton v-if="isSkeletonRow(row.original)" class="ml-auto h-4 w-16" />
            <UDropdownMenu
              v-else
              :items="getRowActionItems(row.original)"
              :content="{ align: 'end' }"
              @click.stop
            >
              <UButton
                icon="i-lucide-ellipsis-vertical"
                color="neutral"
                variant="ghost"
                size="sm"
                :aria-label="t('dataOperations.columns.actions')"
              />
            </UDropdownMenu>
          </template>

          <template #empty>
            <CrudTableEmptyState
              :title="isFiltered ? t('dataOperations.notFound.title') : t('dataOperations.empty.title')"
              :description="isFiltered
                ? t('dataOperations.notFound.description')
                : t('dataOperations.empty.description')"
              :filtered="isFiltered"
              :error="loadError"
              :error-description="t('dataOperations.toasts.loadFailed')"
              @clear-filters="clearAllFilters"
              @retry="refresh"
            />
          </template>
        </CrudDataTable>
      </div>
    </template>
  </UDashboardPanel>

  <!-- Загрузка внешнего дампа: файл кладётся в хранилище, восстановление — отдельным шагом -->
  <UModal
    v-model:open="uploadOpen"
    :title="t('dataOperations.upload.title')"
    :description="t('dataOperations.upload.description')"
  >
    <template #body>
      <div
        class="flex flex-col items-center rounded-lg border border-dashed p-8 text-center transition-colors"
        :class="dragging ? 'border-primary bg-primary/5' : 'border-default'"
        @dragover.prevent="dragging = true"
        @dragleave.prevent="dragging = false"
        @drop.prevent="onDrop"
      >
        <input
          ref="fileInput"
          type="file"
          accept=".gz,.sql.gz,.dump.gz"
          class="sr-only"
          @change="selectFile((($event.target as HTMLInputElement).files ?? [])[0])"
        >
        <UIcon name="i-lucide-file-up" class="size-8 text-dimmed" />
        <p class="mt-3 text-sm font-medium text-highlighted">
          {{ selectedFile ? selectedFile.name : t("dataOperations.upload.dropHere") }}
        </p>
        <p class="mt-1 text-xs text-muted">
          {{
            selectedFile
              ? formatBytes(selectedFile.size)
              : t("dataOperations.upload.hint", { limit: status?.maxUploadMb ?? 1024 })
          }}
        </p>
        <UButton
          class="mt-4"
          :label="selectedFile
            ? t('dataOperations.upload.replace')
            : t('dataOperations.upload.choose')"
          icon="i-lucide-folder-open"
          color="neutral"
          variant="outline"
          @click="fileInput?.click()"
        />
      </div>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton
          :label="t('common.cancel')"
          color="neutral"
          variant="ghost"
          @click="uploadOpen = false"
        />
        <UButton
          :label="t('dataOperations.upload.submit')"
          icon="i-lucide-upload"
          :disabled="!selectedFile"
          :loading="uploading"
          @click="onUpload"
        />
      </div>
    </template>
  </UModal>

  <ConfirmDialog
    :open="restoreTarget !== null"
    :title="t('dataOperations.restore.title')"
    :description="t('dataOperations.restore.description', { file: restoreTarget?.filename ?? '' })"
    :confirm-label="t('dataOperations.actions.restore')"
    confirm-color="error"
    confirm-icon="i-lucide-database-zap"
    :loading="restoring"
    @update:open="restoreTarget = null"
    @confirm="onRestore"
  />

  <ConfirmDialog
    :open="deleteTarget !== null"
    :title="t('dataOperations.delete.title')"
    :description="t('dataOperations.delete.description', { file: deleteTarget?.filename ?? '' })"
    :confirm-label="t('dataOperations.actions.delete')"
    confirm-color="error"
    confirm-icon="i-lucide-trash-2"
    :loading="deleting"
    @update:open="deleteTarget = null"
    @confirm="onDelete"
  />

  <ConfirmDialog
    v-model:open="bulkDeleteOpen"
    :title="t('dataOperations.deleteSelected.title')"
    :description="t('dataOperations.deleteSelected.description', { count: selectedRows.length })"
    :confirm-label="t('dataOperations.actions.delete')"
    confirm-color="error"
    confirm-icon="i-lucide-trash-2"
    :loading="bulkDeleting"
    @confirm="onBulkDelete"
  />
</template>
