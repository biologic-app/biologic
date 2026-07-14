<script setup lang="ts">
import { computed, h, nextTick, onMounted, reactive, ref, resolveComponent, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DropdownMenuItem, TableColumn as NuxtTableColumn } from '@nuxt/ui'
import { apiCreateRequest, apiReadListRequest, apiReadRequest, apiRequest, apiUpdateRequest } from '@/shared/api/client.api'
import AccessEntityDetailModal from '@/shared/ui/AccessEntityDetailModal.vue'
import NotificationsBellButton from '@/shared/ui/NotificationsBellButton.vue'
import CrudDataTable from '@/shared/ui/CrudDataTable.vue'
import CrudTableEmptyState from '@/shared/ui/CrudTableEmptyState.vue'
import CrudFilterModal from '@/shared/ui/CrudFilterModal.vue'
import CrudSearchControl from '@/shared/ui/CrudSearchControl.vue'
import ConfirmDialog from '@/shared/ui/ConfirmDialog.vue'
import RowContextMenu from '@/shared/ui/RowContextMenu.vue'
import { createSkeletonRows, isSkeletonRow, renderSkeletonCell } from '@/shared/ui/table'
import AccessNavigation from '@/modules/access/components/AccessNavigation.vue'
import { useCrudDialog } from '@/shared/composables/useCrudDialog'
import { useOptimistic } from '@/shared/composables/useOptimistic'
import { useServerTable } from '@/shared/composables/useServerTable'
import { useTableColumnVisibility } from '@/shared/composables/useTableSettings'
import { summarizePermissions } from '@/shared/utils/permissions'
import type { Permission, PermissionSummary } from '@/shared/types/permissions'
import { usePermission } from '@/shared/composables/usePermission'
import { clone } from '@/shared/utils/clone'
import type { DetailListItem } from '@/shared/ui/EntityDetailMasterList.vue'

const toast = useToast()
const { can } = usePermission()
const { t } = useI18n()

const confirmDialog = ref<{ open: boolean; title: string; description: string; onConfirm: () => void }>({
  open: false,
  title: "",
  description: "",
  onConfirm: () => { },
});

const deleting = ref(false)
const pendingUndo = ref<Array<{ item: RoleRow; timeout: ReturnType<typeof setTimeout> }>>([]);

function undoDelete(undoEntry: { item: RoleRow; timeout: ReturnType<typeof setTimeout> }) {
  clearTimeout(undoEntry.timeout);
  pendingUndo.value = pendingUndo.value.filter((e) => e !== undoEntry);
  table.data.value = [undoEntry.item, ...table.data.value];
  apiCreateRequest<RoleRow>("/roles", {
    method: "POST",
    body: undoEntry.item,
  }).catch(() => {
    table.data.value = table.data.value.filter((row) => row.id !== undoEntry.item.id);
    toast.add({
      title: t("access.failedToRestoreRole"),
      color: "error",
    });
  });
}

type RoleRow = {
  id: string | number
  key?: string
  name?: string
  scope_type?: string
  permissionsSummary?: PermissionSummary
  [key: string]: unknown
}

const errorMessage = (error: unknown) =>
  error instanceof Error ? error.message : t('access.tryAgain')

const dialog = useCrudDialog<RoleRow>('user-types')
const optimistic = useOptimistic<RoleRow>()
const saving = ref(false)
const permissionsLoading = ref(false)
const permissions = ref<Permission[]>([])
const permissionCatalog = ref<Permission[]>([])
const form = reactive({
  key: '',
  name: '',
  scope_type: 'global' as string
})
const tableSettingsKey = 'table-settings:access:user-types:v2'

const table = useServerTable<RoleRow>(
  (params) => apiReadListRequest<RoleRow>('/roles', { method: 'GET', params }),
  {
    mode: 'infinite',
    presetKey: 'user-types',
    settingsKey: tableSettingsKey,
    filters: {
      global: { value: '', matchMode: 'contains' },
      key: { value: '', matchMode: 'contains' },
      name: { value: '', matchMode: 'contains' },
      updated_at: { value: [null, null], matchMode: 'between' }
    }
  }
)

const filters = reactive(clone(table.filters.value))
const filterModalOpen = ref(false)
const columnVisibility = useTableColumnVisibility(tableSettingsKey)
const rowSelection = ref<Record<string, boolean>>({})
const contextRow = ref<RoleRow | null>(null)
const contextMenuOpen = ref(false)
const contextMenuPosition = ref({ x: 0, y: 0 })
const skeletonRows = createSkeletonRows<RoleRow>(17)

const tableRows = computed(() =>
  table.loading.value ? skeletonRows : table.data.value
)

// Левый master-список модалки доступа: текущие строки таблицы ролей.
const detailListItems = computed<DetailListItem[]>(() =>
  table.data.value.map((row) => ({
    id: row.id,
    title: String(row.name || row.key || `#${row.id}`),
    subtitle: row.key || row.scope_type || '',
  }))
)

const selectListRole = (id: string | number) => {
  const row = table.data.value.find((entry) => String(entry.id) === String(id))
  if (row) {
    dialog.openView(row)
  }
}

const syncFilters = () => {
  Object.entries(table.filters.value).forEach(([key, value]) => {
    filters[key] = { ...value }
  })
}

syncFilters()

watch(
  () => table.filters.value,
  () => syncFilters(),
  { deep: true }
)

watch(
  () => [dialog.visible.value, dialog.selected.value] as const,
  async ([isVisible, selected]) => {
    if (!isVisible) {
      permissions.value = []
      form.key = ''
      form.name = ''
      form.scope_type = 'global'
      return
    }

    form.key = selected?.key || ''
    form.name = selected?.name || ''
    form.scope_type = selected?.scope_type || 'global'

    if (!selected?.id) {
      permissions.value = []
      return
    }

    permissionsLoading.value = true
    try {
      const response = await apiReadRequest<{ permissions: Permission[] }>(`/roles/${selected.id}/permissions`, {
        method: 'GET'
      })
      permissions.value = response.data.permissions
    } catch (error: unknown) {
      toast.add({
        title: t('access.failedToLoadRolePermissions'),
        description: errorMessage(error),
        color: 'error'
      })
    } finally {
      permissionsLoading.value = false
    }
  },
  { immediate: true }
)

const uiColumns = computed<NuxtTableColumn<RoleRow>[]>(() => {
  const UButton = resolveComponent('UButton')
  const UBadge = resolveComponent('UBadge')

  return [
    {
      accessorKey: 'id',
      header: 'ID',
      cell: ({ row }) =>
        isSkeletonRow(row.original) ? renderSkeletonCell('id', 0) : row.original.id
    },
    {
      accessorKey: 'key',
      header: () =>
        h(UButton, {
          color: 'neutral',
          variant: 'ghost',
          label: t('access.columns.key'),
          icon:
            table.sorting.value.field !== 'key'
              ? 'i-lucide-arrow-up-down'
              : table.sorting.value.order === 1
                ? 'i-lucide-arrow-up-narrow-wide'
                : 'i-lucide-arrow-down-wide-narrow',
          onClick: () => table.setSort('key')
        }),
      cell: ({ row }) =>
        isSkeletonRow(row.original) ? renderSkeletonCell('key', 1) : row.original.key
    },
    {
      accessorKey: 'name',
      header: () =>
        h(UButton, {
          color: 'neutral',
          variant: 'ghost',
          label: t('access.columns.name'),
          icon:
            table.sorting.value.field !== 'name'
              ? 'i-lucide-arrow-up-down'
              : table.sorting.value.order === 1
                ? 'i-lucide-arrow-up-narrow-wide'
                : 'i-lucide-arrow-down-wide-narrow',
          onClick: () => table.setSort('name')
        }),
      cell: ({ row }) =>
        isSkeletonRow(row.original) ? renderSkeletonCell('name', 2) : row.original.name
    },
    {
      id: 'summary',
      header: t('access.columns.permissions'),
      cell: ({ row }) => {
        if (isSkeletonRow(row.original)) {
          return renderSkeletonCell('summary', 3)
        }

        const summary = row.original.permissionsSummary || { view: 0, create: 0, edit: 0, delete: 0 }
        const UTooltip = resolveComponent('UTooltip')
        const badges = [
          { key: 'view', short: 'V', label: t('permissions.actionLabels.view') },
          { key: 'create', short: 'C', label: t('permissions.actionLabels.create') },
          { key: 'edit', short: 'E', label: t('permissions.actionLabels.edit') },
          { key: 'delete', short: 'D', label: t('permissions.actionLabels.delete') },
        ]
        return h('div', { class: 'flex flex-wrap gap-1' },
          badges.map(({ key, short, label }) =>
            h(UTooltip, { text: `${label}: ${summary[key as keyof typeof summary]}` }, () =>
              h(UBadge, { color: 'neutral', variant: 'subtle' }, () => `${short} ${summary[key as keyof typeof summary]}`)
            )
          )
        )
      }
    },
    { id: 'actions', header: t('access.columns.actions'), meta: { class: { td: 'w-auto min-w-[56px] text-right' } } }
  ]
})

const updatePermissions = (value: Permission[]) => {
  permissions.value = value
}

const roleFieldOptions = computed(() => ({
  scope_type: [
    { label: t('access.scopeType.global'), value: 'global' },
    { label: t('access.scopeType.ownLab'), value: 'own_lab' },
    { label: t('access.scopeType.ownBranch'), value: 'own_branch' },
    { label: t('access.scopeType.ownObjects'), value: 'own_objects' }
  ]
}))

const accessDialogTitle = computed(() =>
  dialog.mode.value === 'create'
    ? t('access.createRole')
    : dialog.mode.value === 'edit'
      ? t('access.editRole')
      : t('access.viewRole')
)

const applyFilters = (debounceGlobal = false) => {
  table.updateFilters(clone(filters), debounceGlobal)
}

const resetFilters = () => {
  filters.global = { value: '', matchMode: 'contains' }
  filters.key = { value: '', matchMode: 'contains' }
  filters.name = { value: '', matchMode: 'contains' }
  filters.updated_at = { value: [null, null], matchMode: 'between' }
  applyFilters()
}

const activeFilterCount = computed(() =>
  (Object.entries(filters) as Array<[string, { value: unknown }]>).filter(([key, filter]) => {
    if (key === 'global') {
      return false
    }

    const value = filter.value
    if (Array.isArray(value)) {
      return value.some((item) => item !== null && item !== '')
    }

    return value !== null && value !== undefined && value !== ''
  }).length
)

const removeItem = async (row: RoleRow) => {
  confirmDialog.value = {
    open: true,
    title: t("access.deleteRole"),
    description: t("access.deleteRoleConfirm", { name: row.name }),
    async onConfirm() {
      deleting.value = true
      const deletedRow = { ...table.data.value.find((r) => r.id === row.id) || row }
      const rollback = optimistic.removeItem(table.data, row.id)
      try {
        await apiRequest(`/roles/${row.id}`, { method: 'DELETE' })
        const timeout = setTimeout(() => {
          pendingUndo.value = pendingUndo.value.filter((e) => e.item.id !== row.id)
        }, 8000)
        const undoEntry = { item: deletedRow, timeout }
        pendingUndo.value.push(undoEntry)
        toast.add({
          title: t('access.roleDeleted'),
          description: t('access.roleDeletedPending'),
          color: 'success',
          icon: 'i-lucide-circle-check',
          actions: [{
            label: t('access.undo'),
            icon: 'i-lucide-undo-2',
            onClick: () => undoDelete(undoEntry),
          }],
          duration: 8000,
        })
      } catch (error: unknown) {
        rollback()
        toast.add({
          title: t('access.failedToDeleteRole'),
          description: errorMessage(error),
          color: 'error'
        })
      } finally {
        deleting.value = false
        confirmDialog.value.open = false
      }
    },
  }
}

const selectedRows = computed(() =>
  Object.keys(rowSelection.value)
    .filter((key) => rowSelection.value[key])
    .map((key) => table.data.value[Number(key)])
    .filter(Boolean)
)

const selectedCount = computed(() => selectedRows.value.length)

const deleteSelected = async () => {
  if (!selectedRows.value.length) {
    return
  }

  confirmDialog.value = {
    open: true,
    title: t("access.deleteRoles"),
    description: t("access.deleteRolesConfirm", { count: selectedRows.value.length }),
    async onConfirm() {
      deleting.value = true

      const rows = [...selectedRows.value]
      const ids = rows.map((row) => row.id)
      const previous = [...table.data.value]
      table.data.value = table.data.value.filter((row) => !ids.includes(row.id))

      try {
        await Promise.all(rows.map((row) => apiRequest(`/roles/${row.id}`, { method: 'DELETE' })))
        rowSelection.value = {}
        toast.add({
          title: t('access.rolesDeleted'),
          color: 'success',
          icon: 'i-lucide-circle-check',
        })
      } catch (error: unknown) {
        table.data.value = previous
        toast.add({
          title: t('access.failedToDeleteRoles'),
          description: errorMessage(error),
          color: 'error'
        })
      } finally {
        deleting.value = false
        confirmDialog.value.open = false
      }
    },
  }
}

const getRowActionItems = (row: RoleRow): DropdownMenuItem[] => [
  { label: t('access.actions.view'), icon: 'i-lucide-eye', onSelect: () => dialog.openView(row) },
  {
    label: t('access.actions.edit'),
    icon: can('user-types', 'edit') ? 'i-lucide-pencil' : 'i-lucide-lock',
    disabled: !can('user-types', 'edit'),
    onSelect: () => dialog.openEdit(row)
  },
  {
    label: t('access.actions.delete'),
    icon: can('user-types', 'delete') ? 'i-lucide-trash-2' : 'i-lucide-lock',
    color: 'error',
    disabled: !can('user-types', 'delete'),
    onSelect: () => removeItem(row)
  }
]

const handleRowSelect = (_event: Event, row: { original: RoleRow }) => {
  if (isSkeletonRow(row.original)) {
    return
  }

  dialog.openView(row.original)
}

const contextMenuItems = computed(() =>
  contextRow.value ? getRowActionItems(contextRow.value) : []
)

const handleRowContextmenu = async (event: Event, row: { original: RoleRow }) => {
  event.preventDefault()
  if (isSkeletonRow(row.original)) {
    return
  }

  const mouseEvent = event as MouseEvent
  contextRow.value = row.original
  contextMenuOpen.value = false
  contextMenuPosition.value = { x: mouseEvent.clientX, y: mouseEvent.clientY }
  await nextTick()
  contextMenuOpen.value = true
}

const columnLabels = computed<Record<string, string>>(() => ({
  id: 'ID',
  key: t('access.columns.key'),
  name: t('access.columns.name'),
  summary: t('access.columns.permissions'),
  actions: t('access.columns.actions')
}))

const permissionKey = (permission: Pick<Permission, 'resource' | 'action'>) =>
  `${permission.resource}:${permission.action}`

const refreshPermissionCatalog = async () => {
  const response = await apiReadListRequest<Permission>('/permissions', {
    method: 'GET',
    params: { limit: 500 }
  })
  permissionCatalog.value = response.items
}

const ensurePermissionAssignments = async (selected: Permission[]) => {
  const byKey = new Map(permissionCatalog.value.map((permission) => [permissionKey(permission), permission]))
  const assignments: Array<{ permission_id: string; scope: string }> = []

  for (const permission of selected) {
    const key = permissionKey(permission)
    let resolved = permission.id || permission.permission_id || byKey.get(key)?.id

    if (!resolved) {
      const response = await apiCreateRequest<Permission>('/permissions', {
        method: 'POST',
        body: { resource: permission.resource, action: permission.action }
      })
      resolved = response.data.id
      if (!resolved) {
        throw new Error('Backend did not return permission id')
      }
      byKey.set(key, response.data)
      permissionCatalog.value = [...permissionCatalog.value, response.data]
    }

    assignments.push({
      permission_id: resolved,
      scope: permission.scope || 'all'
    })
  }

  return assignments
}

const columnMenuItems = computed(() =>
  Object.entries(columnLabels.value).map(([key, label]) => ({
    label,
    type: 'checkbox' as const,
    checked: columnVisibility.value[key] !== false,
    onUpdateChecked(checked: boolean) {
      columnVisibility.value = {
        ...columnVisibility.value,
        [key]: checked
      }
    },
    onSelect(event?: Event) {
      event?.preventDefault()
    }
  }))
)

const onSave = async (formPayload?: Record<string, unknown>) => {
  const source = formPayload ?? form
  saving.value = true
  try {
    if (dialog.mode.value === 'create') {
      const response = await apiCreateRequest<RoleRow>('/roles', {
        method: 'POST',
        body: { key: source.key, name: source.name, scope_type: source.scope_type || 'global' }
      })

      if (permissions.value.length) {
        const assignments = await ensurePermissionAssignments(permissions.value)
        await apiRequest(`/roles/${response.data.id}/permissions`, {
          method: 'PUT',
          body: { permissions: assignments }
        })
      }

      table.data.value = [
        {
          ...response.data,
          permissionsSummary: summarizePermissions(permissions.value)
        },
        ...table.data.value
      ]
    } else if (dialog.selected.value?.id) {
      const selectedId = dialog.selected.value.id
      const response = await apiUpdateRequest<RoleRow>(`/roles/${selectedId}`, {
        method: 'PATCH',
        body: { key: source.key, name: source.name, scope_type: source.scope_type || 'global' }
      })

      const assignments = await ensurePermissionAssignments(permissions.value)
      await apiRequest(`/roles/${selectedId}/permissions`, {
        method: 'PUT',
        body: { permissions: assignments }
      })

      table.data.value = table.data.value.map((item) =>
        item.id === selectedId
          ? { ...response.data, permissionsSummary: summarizePermissions(permissions.value) }
          : item
      )
    }

    dialog.close()
  } catch (error: unknown) {
    toast.add({
      title: t('access.failedToSaveRole'),
      description: errorMessage(error),
      color: 'error'
    })
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await Promise.all([
    refreshPermissionCatalog().catch(() => { }),
    table.fetch()
  ])
})
</script>

<template>
  <UDashboardPanel id="user-types">
    <template #header>
      <UDashboardNavbar :title="t('access.title')">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <UButton
            :label="t('access.createRole')"
            :icon="can('user-types', 'create') ? 'i-lucide-plus' : 'i-lucide-lock'"
            :disabled="!can('user-types', 'create')"
            @click="dialog.openCreate()"
          />

          <NotificationsBellButton />
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
              :placeholder="t('access.searchRole')"
              @update:model-value="applyFilters(true)"
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
              :label="t('common.delete')"
              @click="deleteSelected"
            >
              <template #trailing>
                <UKbd>{{ selectedCount }}</UKbd>
              </template>
            </UButton>
            <UTooltip :text="t('access.refreshData')">
              <UButton
                :label="t('common.update')"
                color="neutral"
                variant="subtle"
                icon="i-lucide-refresh-cw"
                @click="table.refresh()"
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
        @apply="applyFilters()"
        @reset="resetFilters()"
      >
        <div class="grid gap-3 md:grid-cols-3">
          <UInput v-model="filters.key.value" :placeholder="t('access.columns.key')" />
          <UInput v-model="filters.name.value" :placeholder="t('access.columns.name')" />
          <div class="grid gap-2 sm:grid-cols-2">
            <UInput
              :model-value="filters.updated_at.value?.[0] || ''"
              type="date"
              @update:model-value="
                filters.updated_at.value = [$event || null, filters.updated_at.value?.[1] || null]
              "
            />
            <UInput
              :model-value="filters.updated_at.value?.[1] || ''"
              type="date"
              @update:model-value="
                filters.updated_at.value = [filters.updated_at.value?.[0] || null, $event || null]
              "
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
        selectable
        :can-delete="can('user-types', 'delete')"
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
          <UDropdownMenu v-else :content="{ align: 'end' }" :items="getRowActionItems(row.original)">
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
            :title="activeFilterCount ? t('access.notFound') : t('access.noRoles')"
            :description="activeFilterCount
              ? t('access.noRolesMatching')
              : t('access.changeFiltersOrCreateRole')"
            :filtered="activeFilterCount > 0"
            :error="table.error.value"
            :error-description="t('access.failedToLoadRoles')"
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
    kind="role"
    :mode="dialog.mode.value"
    :item="dialog.selected.value"
    :loading="permissionsLoading"
    :saving="saving"
    :read-only="dialog.readOnly.value"
    :editable="can('user-types', 'edit')"
    :permissions="permissions"
    :field-options="roleFieldOptions"
    :list-items="detailListItems"
    :selected-id="dialog.selected.value?.id ?? null"
    :list-has-more="table.hasMore.value"
    :list-loading-more="table.loadingMore.value"
    @update:permissions="updatePermissions"
    @edit="dialog.startEdit()"
    @save="onSave"
    @select="selectListRole"
    @list-load-more="table.loadMore()"
  />

  <ConfirmDialog
    v-model:open="confirmDialog.open"
    :title="confirmDialog.title"
    :description="confirmDialog.description"
    :loading="deleting"
    confirm-color="error"
    :confirm-label="t('common.delete')"
    confirm-icon="i-lucide-trash-2"
    @confirm="confirmDialog.onConfirm"
  />
</template>
