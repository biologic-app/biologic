<script setup lang="ts">
import {
  computed,
  h,
  nextTick,
  onMounted,
  reactive,
  ref,
  resolveComponent,
  watch,
} from "vue";
import type { DropdownMenuItem, TableColumn as NuxtTableColumn } from "@nuxt/ui";
import {
  apiCreateRequest,
  apiReadListRequest,
  apiReadRequest,
  apiRequest,
  apiUpdateRequest,
  loadReferenceOptions,
} from "@/shared/api/client.api";
import AccessEntityDetailModal from "@/shared/ui/AccessEntityDetailModal.vue";
import CrudDataTable from "@/shared/ui/CrudDataTable.vue";
import CrudTableEmptyState from "@/shared/ui/CrudTableEmptyState.vue";
import CrudFilterControls from "@/shared/ui/CrudFilterControls.vue";
import CrudFilterModal from "@/shared/ui/CrudFilterModal.vue";
import CrudSearchControl from "@/shared/ui/CrudSearchControl.vue";
import ConfirmDialog from "@/shared/ui/ConfirmDialog.vue";
import RowContextMenu from "@/shared/ui/RowContextMenu.vue";
import { createSkeletonRows, isSkeletonRow, renderSkeletonCell } from "@/shared/ui/table";
import AccessNavigation from "@/modules/access/components/AccessNavigation.vue";
import { useCrudDialog } from "@/shared/composables/useCrudDialog";
import { useOptimistic } from "@/shared/composables/useOptimistic";
import { useServerTable } from "@/shared/composables/useServerTable";
import { useTableColumnVisibility } from "@/shared/composables/useTableSettings";
import type {
  Permission,
  PermissionOverride,
} from "@/shared/types/permissions";
import { useAuth } from "@/modules/auth/composables/useAuth";

const toast = useToast();
const auth = useAuth();
const can = (resource?: unknown, action?: unknown) => {
  void resource;
  void action;
  return true;
};

const confirmDialog = ref<{ open: boolean; title: string; description: string; onConfirm: () => void }>({
  open: false,
  title: "",
  description: "",
  onConfirm: () => {},
});

const deleting = ref(false);
const pendingUndo = ref<Array<{ item: UserRow; timeout: ReturnType<typeof setTimeout> }>>([]);

function undoDelete(undoEntry: { item: UserRow; timeout: ReturnType<typeof setTimeout> }) {
  clearTimeout(undoEntry.timeout);
  pendingUndo.value = pendingUndo.value.filter((e) => e !== undoEntry);
  table.data.value = [undoEntry.item, ...table.data.value];
  apiCreateRequest<UserRow>("/users", {
    method: "POST",
    body: undoEntry.item,
  }).catch(() => {
    table.data.value = table.data.value.filter((row) => row.id !== undoEntry.item.id);
    toast.add({
      title: "Не удалось восстановить пользователя",
      color: "error",
    });
  });
}

type UserRow = {
  id: string | number;
  username?: string;
  code?: string;
  first_name?: string;
  last_name?: string;
  patronymic?: string;
  role_id?: string | number | boolean | null;
  lab_id?: string | number | boolean | null;
  is_registrar?: boolean;
  is_lab_head?: boolean;
  is_branch_head?: boolean;
  role?: { name?: string | null } | null;
  lab?: { name?: string | null } | null;
  [key: string]: unknown;
};

const errorMessage = (error: unknown) =>
  error instanceof Error ? error.message : "Попробуйте ещё раз";

const dialog = useCrudDialog<UserRow>("users");
const optimistic = useOptimistic<UserRow>();
const saving = ref(false);
const rolePermissions = ref<Permission[]>([]);
const overrides = ref<PermissionOverride[]>([]);
const permissionCatalog = ref<Permission[]>([]);
const permissionsLoading = ref(false);
const roleOptions = ref<
  Array<{ label: string; value: string | number | boolean | null }>
>([]);
const labOptions = ref<
  Array<{ label: string; value: string | number | boolean | null }>
>([]);
const form = reactive({
  username: "",
  code: "",
  first_name: "",
  last_name: "",
  patronymic: "",
  role_id: "",
  lab_id: null as string | number | boolean | null,
  is_registrar: false,
  is_lab_head: false,
  is_branch_head: false,
  password_hash: "",
});
const tableSettingsKey = "table-settings:access:users:v2";

const table = useServerTable<UserRow>(
  (params) =>
    apiReadListRequest<UserRow>("/users", {
      method: "GET",
      params: {
        ...params,
        include: "role,lab",
      },
    }),
  {
    mode: "infinite",
    presetKey: "users",
    settingsKey: tableSettingsKey,
    filters: {
      global: { value: "", matchMode: "contains" },
      username: { value: "", matchMode: "contains" },
      code: { value: "", matchMode: "contains" },
      first_name: { value: "", matchMode: "contains" },
      last_name: { value: "", matchMode: "contains" },
      "role.name": { value: "", matchMode: "contains" },
      "lab.name": { value: "", matchMode: "contains" },
      is_registrar: { value: [], matchMode: "in" },
      updated_at: { value: [null, null], matchMode: "between" },
    },
  },
);

const filters = reactive(JSON.parse(JSON.stringify(table.filters.value)));
const filterModalOpen = ref(false);
const columnVisibility = useTableColumnVisibility(tableSettingsKey);
const rowSelection = ref<Record<string, boolean>>({});
const contextRow = ref<UserRow | null>(null);
const contextMenuOpen = ref(false);
const contextMenuPosition = ref({ x: 0, y: 0 });
const skeletonRows = createSkeletonRows<UserRow>(17);

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
  () => syncFilters(),
  { deep: true },
);

watch(
  () => [dialog.visible.value, dialog.selected.value] as const,
  async ([isVisible, selected]) => {
    if (!isVisible) {
      rolePermissions.value = [];
      overrides.value = [];
      form.username = "";
      form.code = "";
      form.first_name = "";
      form.last_name = "";
      form.patronymic = "";
      form.role_id = "";
      form.lab_id = null;
      form.is_registrar = false;
      form.is_lab_head = false;
      form.is_branch_head = false;
      form.password_hash = "";
      return;
    }

    form.username = selected?.username || "";
    form.code = selected?.code || "";
    form.first_name = selected?.first_name || "";
    form.last_name = selected?.last_name || "";
    form.patronymic = selected?.patronymic || "";
    form.role_id = selected?.role_id ? String(selected.role_id) : "";
    form.lab_id = selected?.lab_id || null;
    form.is_registrar = Boolean(selected?.is_registrar);
    form.is_lab_head = Boolean(selected?.is_lab_head);
    form.is_branch_head = Boolean(selected?.is_branch_head);
    form.password_hash = "";

    if (!selected?.id) {
      rolePermissions.value = [];
      overrides.value = [];
      return;
    }

    permissionsLoading.value = true;
    try {
      const [roleResponse, overridesResponse] = await Promise.all([
        selected.role_id
          ? apiReadRequest<{ permissions: Permission[] }>(`/roles/${selected.role_id}/permissions`, {
              method: "GET",
            })
          : Promise.resolve({ data: { permissions: [] } }),
        apiReadRequest<{ overrides: PermissionOverride[] }>(`/users/${selected.id}/overrides`, {
          method: "GET",
        }),
      ]);
      rolePermissions.value = roleResponse.data.permissions;
      overrides.value = overridesResponse.data.overrides;
    } catch (error: unknown) {
      toast.add({
        title: "Не удалось загрузить права пользователя",
        description: errorMessage(error),
        color: "error",
      });
    } finally {
      permissionsLoading.value = false;
    }
  },
  { immediate: true },
);

const uiColumns = computed<NuxtTableColumn<UserRow>[]>(() => {
  const UButton = resolveComponent("UButton");
  const UBadge = resolveComponent("UBadge");

  return [
    {
      accessorKey: "id",
      header: "ID",
      cell: ({ row }) =>
        isSkeletonRow(row.original) ? renderSkeletonCell("id", 0) : row.original.id,
    },
    {
      accessorKey: "username",
      header: () =>
        h(UButton, {
          color: "neutral",
          variant: "ghost",
          label: "Логин",
          icon:
            table.sorting.value.field !== "username"
              ? "i-lucide-arrow-up-down"
              : table.sorting.value.order === 1
                ? "i-lucide-arrow-up-narrow-wide"
                : "i-lucide-arrow-down-wide-narrow",
          onClick: () => table.setSort("username"),
        }),
      cell: ({ row }) =>
        isSkeletonRow(row.original) ? renderSkeletonCell("username", 1) : row.original.username,
    },
    {
      accessorKey: "first_name",
      header: "Имя",
      cell: ({ row }) =>
        isSkeletonRow(row.original) ? renderSkeletonCell("first_name", 2) : row.original.first_name || "-",
    },
    {
      accessorKey: "last_name",
      header: "Фамилия / Отчество",
      cell: ({ row }) =>
        isSkeletonRow(row.original)
          ? renderSkeletonCell("last_name", 3)
          :
        [row.original.last_name, row.original.patronymic]
          .filter(Boolean)
          .join(" ") || "-",
    },
    {
      accessorKey: "role.name",
      header: "Роль",
      cell: ({ row }) =>
        isSkeletonRow(row.original) ? renderSkeletonCell("role.name", 4) : row.original.role?.name || "-",
    },
    {
      accessorKey: "lab.name",
      header: "Лаборатория",
      cell: ({ row }) =>
        isSkeletonRow(row.original) ? renderSkeletonCell("lab.name", 5) : row.original.lab?.name || "-",
    },
    {
      accessorKey: "is_registrar",
      header: "Регистратор",
      cell: ({ row }) =>
        isSkeletonRow(row.original)
          ? renderSkeletonCell("is_registrar", 6)
          :
        h(
          UBadge,
          {
            color: "neutral",
            variant: "subtle",
          },
          () => (row.original.is_registrar ? "Да" : "Нет"),
        ),
    },
    { id: "actions", header: "Действия", meta: { class: { td: "w-auto min-w-[56px] text-right" } } },
  ];
});

const updateOverrides = (value: PermissionOverride[]) => {
  overrides.value = value;
};

const permissionKey = (permission: Pick<Permission, "resource" | "action">) =>
  `${permission.resource}:${permission.action}`;

const refreshPermissionCatalog = async () => {
  const response = await apiReadListRequest<Permission>("/permissions", {
    method: "GET",
    params: { limit: 500 },
  });
  permissionCatalog.value = response.items;
};

const ensureOverrideAssignments = async (selected: PermissionOverride[]) => {
  const byKey = new Map(permissionCatalog.value.map((permission) => [permissionKey(permission), permission]));
  const assignments: Array<{ permission_id: string; allowed: boolean; scope: string | null }> = [];

  for (const override of selected) {
    const key = permissionKey(override);
    let resolved = override.permission_id || byKey.get(key)?.id;

    if (!resolved) {
      const response = await apiCreateRequest<Permission>("/permissions", {
        method: "POST",
        body: { resource: override.resource, action: override.action },
      });
      resolved = response.data.id;
      if (!resolved) {
        throw new Error("Backend did not return permission id");
      }
      byKey.set(key, response.data);
      permissionCatalog.value = [...permissionCatalog.value, response.data];
    }

    assignments.push({
      permission_id: resolved,
      allowed: override.allowed,
      scope: override.allowed ? override.scope || "all" : null,
    });
  }

  return assignments;
};

const accessDialogTitle = computed(() =>
  dialog.mode.value === "create"
    ? "Создать пользователя"
    : dialog.mode.value === "edit"
      ? "Редактировать пользователя"
      : "Просмотр пользователя",
);

const accessFieldOptions = computed(() => ({
  role_id: roleOptions.value,
  lab_id: labOptions.value,
}));

const applyFilters = (debounceGlobal = false) => {
  table.updateFilters(JSON.parse(JSON.stringify(filters)), debounceGlobal);
};

const resetFilters = () => {
  Object.keys(table.filters.value).forEach((key) => {
    filters[key] = { value: Array.isArray(table.filters.value[key].value) ? [] : "", matchMode: table.filters.value[key].matchMode };
  });
  filters.updated_at = { value: [null, null], matchMode: "between" };
  filters.is_registrar = { value: [], matchMode: "in" };
  applyFilters();
};

const activeFilterCount = computed(() =>
  (Object.entries(filters) as Array<[string, { value: unknown }]>).filter(([key, filter]) => {
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

const removeItem = async (row: UserRow) => {
  confirmDialog.value = {
    open: true,
    title: "Удалить пользователя",
    description: `Вы уверены, что хотите удалить пользователя ${row.username}? Это действие нельзя отменить.`,
    async onConfirm() {
      deleting.value = true;
      const deletedRow = { ...table.data.value.find((r) => r.id === row.id) || row };
      const rollback = optimistic.removeItem(table.data, row.id);
      try {
        await apiRequest(`/users/${row.id}`, { method: "DELETE" });
        const timeout = setTimeout(() => {
          pendingUndo.value = pendingUndo.value.filter((e) => e.item.id !== row.id);
        }, 8000);
        const undoEntry = { item: deletedRow, timeout };
        pendingUndo.value.push(undoEntry);
        toast.add({
          title: "Пользователь удалён",
          description: "Пользователь будет удалён безвозвратно через 8 секунд.",
          color: "success",
          icon: "i-lucide-circle-check",
          actions: [{
            label: "Отменить",
            icon: "i-lucide-undo-2",
            onClick: () => undoDelete(undoEntry),
          }],
          duration: 8000,
        });
      } catch (error: unknown) {
        rollback();
        toast.add({
          title: "Не удалось удалить пользователя",
          description: errorMessage(error),
          color: "error",
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
    title: "Удалить пользователей",
    description: `Вы уверены, что хотите удалить ${selectedRows.value.length} пользователей? Это действие нельзя отменить.`,
    async onConfirm() {
      deleting.value = true;

      const rows = [...selectedRows.value];
      const ids = rows.map((row) => row.id);
      const previous = [...table.data.value];
      table.data.value = table.data.value.filter((row) => !ids.includes(row.id));

      try {
        await Promise.all(rows.map((row) => apiRequest(`/users/${row.id}`, { method: "DELETE" })));
        rowSelection.value = {};
        toast.add({
          title: "Пользователи удалены",
          color: "success",
          icon: "i-lucide-circle-check",
        });
      } catch (error: unknown) {
        table.data.value = previous;
        toast.add({
          title: "Не удалось удалить пользователей",
          description: errorMessage(error),
          color: "error",
        });
      } finally {
        deleting.value = false;
        confirmDialog.value.open = false;
      }
    },
  };
};

const getRowActionItems = (row: UserRow): DropdownMenuItem[] => [
  { label: "Просмотр", icon: "i-lucide-eye", onSelect: () => dialog.openView(row) },
  {
    label: "Редактировать",
    icon: can("users", "edit") ? "i-lucide-pencil" : "i-lucide-lock",
    disabled: !can("users", "edit"),
    onSelect: () => dialog.openEdit(row),
  },
  {
    label: "Удалить",
    icon: can("users", "delete") ? "i-lucide-trash-2" : "i-lucide-lock",
    color: "error",
    disabled: !can("users", "delete"),
    onSelect: () => removeItem(row),
  },
];

const handleRowSelect = (_event: Event, row: { original: UserRow }) => {
  if (isSkeletonRow(row.original)) {
    return;
  }

  dialog.openView(row.original);
};

const contextMenuItems = computed(() =>
  contextRow.value ? getRowActionItems(contextRow.value) : [],
);

const handleRowContextmenu = async (event: Event, row: { original: UserRow }) => {
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

const columnLabels: Record<string, string> = {
  id: "ID",
  username: "Логин",
  first_name: "Имя",
  last_name: "Фамилия / Отчество",
  "role.name": "Роль",
  "lab.name": "Лаборатория",
  is_registrar: "Регистратор",
  actions: "Действия",
};

const columnMenuItems = computed(() =>
  Object.entries(columnLabels).map(([key, label]) => ({
    label,
    type: "checkbox" as const,
    checked: columnVisibility.value[key] !== false,
    onUpdateChecked(checked: boolean) {
      columnVisibility.value = {
        ...columnVisibility.value,
        [key]: checked,
      };
    },
    onSelect(event?: Event) {
      event?.preventDefault();
    },
  })),
);

const onSave = async (formPayload?: Record<string, unknown>) => {
  const source = formPayload ?? form;
  const password = typeof source.password_hash === "string" ? source.password_hash : "";
  saving.value = true;
  try {
    const payload: Record<string, unknown> = {
      username: source.username || null,
      code: source.code || null,
      first_name: source.first_name || null,
      last_name: source.last_name || null,
      patronymic: source.patronymic || null,
      role_id: source.role_id || null,
      lab_id: source.lab_id || null,
      is_registrar: Boolean(source.is_registrar),
      is_lab_head: Boolean(source.is_lab_head),
      is_branch_head: Boolean(source.is_branch_head),
    };

    if (password.trim()) {
      payload.password_hash = password;
    }

    if (dialog.mode.value === "create") {
      const response = await apiCreateRequest<UserRow>("/users", {
        method: "POST",
        body: payload,
      });

      if (overrides.value.length) {
        const overrideAssignments = await ensureOverrideAssignments(overrides.value);
        await apiRequest(`/users/${response.data.id}/overrides`, {
          method: "PUT",
          body: { overrides: overrideAssignments },
        });
      }

      table.data.value = [
        { ...response.data, overridesCount: overrides.value.length },
        ...table.data.value,
      ];
    } else if (dialog.selected.value?.id) {
      const selectedId = dialog.selected.value.id;
      const response = await apiUpdateRequest<UserRow>(`/users/${selectedId}`, {
        method: "PATCH",
        body: payload,
      });

      const overrideAssignments = await ensureOverrideAssignments(overrides.value);
      await apiRequest(`/users/${selectedId}/overrides`, {
        method: "PUT",
        body: { overrides: overrideAssignments },
      });

      table.data.value = table.data.value.map((item) =>
        item.id === selectedId
          ? { ...response.data, overridesCount: overrides.value.length }
          : item,
      );

      if (String(auth.user?.id) === String(selectedId)) {
        await auth.restoreSession();
      }
    }

    dialog.close();
  } catch (error: unknown) {
    toast.add({
      title: "Не удалось сохранить пользователя",
      description: errorMessage(error),
      color: "error",
    });
  } finally {
    saving.value = false;
  }
};

onMounted(async () => {
  const [roles, labs] = await Promise.all([
    loadReferenceOptions("/roles").catch(() => []),
    loadReferenceOptions("/labs").catch(() => []),
    refreshPermissionCatalog().catch(() => {}),
  ]);
  roleOptions.value = roles;
  labOptions.value = labs;
  await table.fetch();
});
</script>

<template>
  <UDashboardPanel id="users">
    <template #header>
      <UDashboardNavbar title="Доступ">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <UButton
            label="Создать пользователя"
            :icon="can('users', 'create') ? 'i-lucide-plus' : 'i-lucide-lock'"
            :disabled="!can('users', 'create')"
            @click="dialog.openCreate()"
          />
        </template>
      </UDashboardNavbar>

      <UDashboardToolbar>
        <AccessNavigation />
      </UDashboardToolbar>

      <UDashboardToolbar>
        <template #left>
          <div class="flex w-full flex-col gap-3 lg:flex-row lg:items-center">
            <CrudSearchControl
              v-model="filters.global.value"
              placeholder="Поиск пользователя"
              @update:model-value="applyFilters(true)"
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
            <UButton
              v-show="selectedCount"
              color="error"
              variant="subtle"
              icon="i-lucide-trash"
              label="Удалить"
              @click="deleteSelected"
            >
              <template #trailing>
                <UKbd>{{ selectedCount }}</UKbd>
              </template>
            </UButton>
            <UButton
              color="neutral"
              variant="subtle"
              icon="i-lucide-refresh-cw"
              label="Обновить"
              @click="table.refresh()"
            />
            <UDropdownMenu
              :items="columnMenuItems"
              :content="{ align: 'end' }"
            >
              <UButton
                label="Столбцы"
                color="neutral"
                variant="subtle"
                trailing-icon="i-lucide-settings-2"
              />
            </UDropdownMenu>
          </div>
        </template>
      </UDashboardToolbar>
    </template>

    <template #body>
      <CrudFilterModal
        v-model:open="filterModalOpen"
        :active-count="activeFilterCount"
        @apply="applyFilters()"
        @reset="resetFilters()"
      >
        <div class="grid gap-3 md:grid-cols-2">
          <UInput
            v-model="filters.username.value"
            placeholder="Логин"
          />
          <UInput
            v-model="filters.code.value"
            placeholder="Код"
          />
          <UInput
            v-model="filters['role.name'].value"
            placeholder="Роль"
          />
          <UInput
            v-model="filters['lab.name'].value"
            placeholder="Лаборатория"
          />
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
        selectable
        @load-more="table.loadMore()"
        @row-select="handleRowSelect"
        @row-contextmenu="handleRowContextmenu"
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
        <template #empty>
          <CrudTableEmptyState
            :title="activeFilterCount ? 'Ничего не найдено' : 'Пользователи не найдены'"
            :description="activeFilterCount
              ? 'Нет пользователей, соответствующих фильтрам. Измените условия поиска.'
              : 'Измените фильтры или создайте нового пользователя.'"
            :filtered="activeFilterCount > 0"
            :error="table.error.value"
            error-description="Не удалось загрузить пользователей. Проверьте подключение или повторите попытку позже."
            @clear-filters="resetFilters"
            @retry="table.refresh()"
          />
        </template>
      </CrudDataTable>
    </template>
  </UDashboardPanel>

  <AccessEntityDetailModal
    v-model:open="dialog.visible.value"
    :title="accessDialogTitle"
    kind="user"
    :mode="dialog.mode.value"
    :item="dialog.selected.value"
    :loading="permissionsLoading"
    :saving="saving"
    :read-only="dialog.readOnly.value"
    :editable="can('users', 'edit')"
    :role-permissions="rolePermissions"
    :overrides="overrides"
    :field-options="accessFieldOptions"
    @update:overrides="updateOverrides"
    @edit="dialog.startEdit()"
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
