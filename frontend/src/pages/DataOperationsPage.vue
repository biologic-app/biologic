<script setup lang="ts">
// Страница «Данные» — экспорт/импорт всей базы. Дамп лежит файлом в файловой
// системе сервера, в БД хранится только путь (таблица database_backups), поэтому
// таблица ниже — это реестр файлов, а не сами данные.
import { computed, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import type { TableColumn } from "@nuxt/ui";
import ConfirmDialog from "@/shared/ui/ConfirmDialog.vue";
import NotificationsBellButton from "@/shared/ui/NotificationsBellButton.vue";
import {
  createBackup,
  deleteBackup,
  downloadBackup,
  fetchBackups,
  fetchDatabaseStatus,
  restoreBackup,
  uploadBackup,
} from "@/modules/database/api/database.api";
import type { BackupStatus, DatabaseBackup, DatabaseStatus } from "@/modules/database/types";
import { formatDateTime } from "@/shared/utils/format";

const { t } = useI18n();
const toast = useToast();

const status = ref<DatabaseStatus | null>(null);
const backups = ref<DatabaseBackup[]>([]);
const loading = ref(false);
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

async function refresh() {
  loading.value = true;
  try {
    const [nextStatus, nextBackups] = await Promise.all([fetchDatabaseStatus(), fetchBackups()]);
    status.value = nextStatus;
    backups.value = nextBackups;
  } catch (error) {
    notifyError(t("dataOperations.toasts.loadFailed"), error);
  } finally {
    loading.value = false;
  }
}

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

const columns = computed<TableColumn<DatabaseBackup>[]>(() => [
  { accessorKey: "filename", header: t("dataOperations.columns.file") },
  { accessorKey: "status", header: t("dataOperations.columns.status") },
  { accessorKey: "origin", header: t("dataOperations.columns.origin") },
  { accessorKey: "sizeBytes", header: t("dataOperations.columns.size") },
  { accessorKey: "durationMs", header: t("dataOperations.columns.duration") },
  { id: "actions" },
]);
</script>

<template>
  <UDashboardPanel id="data-operations">
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
          <p class="text-sm text-muted">
            {{ t("dataOperations.subtitle") }}
          </p>
        </template>
        <template #right>
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
        </template>
      </UDashboardToolbar>
    </template>

    <template #body>
      <div class="flex flex-col gap-4">
        <UAlert
          v-if="status && !status.reachable"
          color="error"
          variant="subtle"
          icon="i-lucide-database-zap"
          :title="t('dataOperations.unreachable')"
          :description="status.error ?? undefined"
        />

        <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
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

        <UTable
          :data="backups"
          :columns="columns"
          :loading="loading"
          class="rounded-lg border border-default"
        >
          <template #filename-cell="{ row }">
            <div class="min-w-0">
              <p class="truncate text-sm font-medium text-highlighted">
                {{ row.original.filename }}
              </p>
              <p class="text-xs text-muted">
                {{ formatDateTime(row.original.createdAt) }}
              </p>
            </div>
          </template>

          <template #status-cell="{ row }">
            <div class="flex flex-col items-start gap-1">
              <UBadge
                :color="STATUS_COLOR[row.original.status]"
                variant="subtle"
                :label="t(`dataOperations.status.${row.original.status}`)"
              />
              <span v-if="row.original.error" class="text-xs text-error">
                {{ row.original.error }}
              </span>
              <span v-else-if="!row.original.fileExists" class="text-xs text-warning">
                {{ t("dataOperations.fileMissing") }}
              </span>
              <span v-else-if="row.original.restoredAt" class="text-xs text-muted">
                {{ t("dataOperations.restoredAt", { date: formatDateTime(row.original.restoredAt) }) }}
              </span>
            </div>
          </template>

          <template #origin-cell="{ row }">
            <div class="flex items-center gap-2">
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
            <span class="text-sm tabular-nums">{{ formatBytes(row.original.sizeBytes) }}</span>
          </template>

          <template #durationMs-cell="{ row }">
            <span class="text-sm tabular-nums text-muted">
              {{ formatDuration(row.original.durationMs) }}
            </span>
          </template>

          <template #actions-cell="{ row }">
            <div class="flex justify-end gap-1">
              <UTooltip :text="t('dataOperations.actions.download')">
                <UButton
                  icon="i-lucide-download"
                  color="neutral"
                  variant="ghost"
                  :disabled="!row.original.fileExists"
                  :aria-label="t('dataOperations.actions.download')"
                  @click="onDownload(row.original)"
                />
              </UTooltip>
              <UTooltip :text="t('dataOperations.actions.restore')">
                <UButton
                  icon="i-lucide-database-zap"
                  color="primary"
                  variant="ghost"
                  :disabled="!row.original.fileExists || row.original.status !== 'completed'"
                  :aria-label="t('dataOperations.actions.restore')"
                  @click="restoreTarget = row.original"
                />
              </UTooltip>
              <UTooltip :text="t('dataOperations.actions.delete')">
                <UButton
                  icon="i-lucide-trash-2"
                  color="error"
                  variant="ghost"
                  :aria-label="t('dataOperations.actions.delete')"
                  @click="deleteTarget = row.original"
                />
              </UTooltip>
            </div>
          </template>

          <template #empty>
            <div class="py-10 text-center">
              <UIcon name="i-lucide-database-backup" class="size-8 text-dimmed" />
              <p class="mt-2 text-sm font-medium text-highlighted">
                {{ t("dataOperations.empty.title") }}
              </p>
              <p class="mt-1 text-xs text-muted">
                {{ t("dataOperations.empty.description") }}
              </p>
            </div>
          </template>
        </UTable>
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
          accept=".dump,.sql,.backup,.bin"
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
</template>
