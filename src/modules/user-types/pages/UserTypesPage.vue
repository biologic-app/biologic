<script setup lang="ts">
import { computed, h, nextTick, onMounted, reactive, ref, resolveComponent, watch } from 'vue'
import type { DropdownMenuItem, TableColumn as NuxtTableColumn } from '@nuxt/ui'
import { apiCreateRequest, apiReadListRequest, apiReadRequest, apiRequest, apiUpdateRequest } from '@/shared/api/client.api'
import AccessEntityDetailModal from '@/shared/ui/AccessEntityDetailModal.vue'
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

const toast = useToast()
const { can } = usePermission()

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
      title: "Не удалось восстановить роль",
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
  error instanceof Error ? error.message : 'Попробуйте ещё раз'

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

const filters = reactive(JSON.parse(JSON.stringify(table.filters.value)))
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
        title: 'Не удалось загрузить права роли',
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
          label: 'Ключ',
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
          label: 'Название',
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
      header: 'Права',
      cell: ({ row }) => {
        if (isSkeletonRow(row.original)) {
          return renderSkeletonCell('summary', 3)
        }

        const summary = row.original.permissionsSummary || { view: 0, create: 0, edit: 0, delete: 0 }
        const UTooltip = resolveComponent('UTooltip')
        const badges = [
          { key: 'view', short: 'V', label: 'Просмотр' },
          { key: 'create', short: 'C', label: 'Создание' },
          { key: 'edit', short: 'E', label: 'Редактирование' },
          { key: 'delete', short: 'D', label: 'Удаление' },
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
    { id: 'actions', header: 'Действия', meta: { class: { td: 'w-auto min-w-[56px] text-right' } } }
  ]
})

const updatePermissions = (value: Permission[]) => {
  permissions.value = value
}

const roleFieldOptions = {
  scope_type: [
    { label: 'Глобально', value: 'global' },
    { label: 'Своя лаборатория', value: 'own_lab' },
    { label: 'Свой филиал', value: 'own_branch' },
    { label: 'Свои объекты', value: 'own_objects' }
  ]
}

const accessDialogTitle = computed(() =>
  dialog.mode.value === 'create'
    ? 'Создать роль'
    : dialog.mode.value === 'edit'
      ? 'Редактировать роль'
      : 'Просмотр роли'
)

const applyFilters = (debounceGlobal = false) => {
  table.updateFilters(JSON.parse(JSON.stringify(filters)), debounceGlobal)
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
    title: "Удалить роль",
    description: `Вы уверены, что хотите удалить роль "${row.name}"? Это действие нельзя отменить.`,
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
          title: 'Роль удалена',
          description: 'Роль будет удалена безвозвратно через 8 секунд.',
          color: 'success',
          icon: 'i-lucide-circle-check',
          actions: [{
            label: 'Отменить',
            icon: 'i-lucide-undo-2',
            onClick: () => undoDelete(undoEntry),
          }],
          duration: 8000,
        })
      } catch (error: unknown) {
        rollback()
        toast.add({
          title: 'Не удалось удалить роль',
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
    title: "Удалить роли",
    description: `Вы уверены, что хотите удалить ${selectedRows.value.length} ролей? Это действие нельзя отменить.`,
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
          title: 'Роли удалены',
          color: 'success',
          icon: 'i-lucide-circle-check',
        })
      } catch (error: unknown) {
        table.data.value = previous
        toast.add({
          title: 'Не удалось удалить роли',
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
  { label: 'Просмотр', icon: 'i-lucide-eye', onSelect: () => dialog.openView(row) },
  {
    label: 'Редактировать',
    icon: can('user-types', 'edit') ? 'i-lucide-pencil' : 'i-lucide-lock',
    disabled: !can('user-types', 'edit'),
    onSelect: () => dialog.openEdit(row)
  },
  {
    label: 'Удалить',
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

const columnLabels: Record<string, string> = {
  id: 'ID',
  key: 'Ключ',
  name: 'Название',
  summary: 'Права',
  actions: 'Действия'
}

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
  Object.entries(columnLabels).map(([key, label]) => ({
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
      title: 'Не удалось сохранить роль',
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
      <UDashboardNavbar title="Доступ">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <UButton label="Создать роль" :icon="can('user-types', 'create') ? 'i-lucide-plus' : 'i-lucide-lock'"
            :disabled="!can('user-types', 'create')" @click="dialog.openCreate()" />
        </template>
      </UDashboardNavbar>

      <UDashboardToolbar>
        <AccessNavigation />
      </UDashboardToolbar>

      <UDashboardToolbar>
        <template #left>
          <div class="flex w-full flex-col gap-3 lg:flex-row lg:items-center">
            <CrudSearchControl v-model="filters.global.value" placeholder="Поиск роли"
              @update:model-value="applyFilters(true)" />
          </div>
        </template>
        <template #right>
          <div class="flex flex-wrap items-center gap-2">
            <UButton v-show="selectedCount" color="error" variant="subtle" icon="i-lucide-trash" label="Удалить"
              @click="deleteSelected">
              <template #trailing>
                <UKbd>{{ selectedCount }}</UKbd>
              </template>
            </UButton>
            <UTooltip text="Обновить данные">

              <UButton color="neutral" variant="subtle" icon="i-lucide-refresh-cw" @click="table.refresh()" />
            </UTooltip>
            <UDropdownMenu :items="columnMenuItems" :content="{ align: 'end' }">
              <UTooltip text="Столбцы таблицы">

                <UButton color="neutral" variant="subtle" trailing-icon="i-lucide-settings-2" />
              </UTooltip>
            </UDropdownMenu>
          </div>
        </template>
      </UDashboardToolbar>
    </template>

    <template #body>
      <CrudFilterModal v-model:open="filterModalOpen" :active-count="activeFilterCount" @apply="applyFilters()"
        @reset="resetFilters()">
        <div class="grid gap-3 md:grid-cols-3">
          <UInput v-model="filters.key.value" placeholder="Ключ" />
          <UInput v-model="filters.name.value" placeholder="Название" />
          <div class="grid gap-2 sm:grid-cols-2">
            <UInput :model-value="filters.updated_at.value?.[0] || ''" type="date" @update:model-value="
              filters.updated_at.value = [$event || null, filters.updated_at.value?.[1] || null]
              " />
            <UInput :model-value="filters.updated_at.value?.[1] || ''" type="date" @update:model-value="
              filters.updated_at.value = [filters.updated_at.value?.[0] || null, $event || null]
              " />
          </div>
        </div>
      </CrudFilterModal>

      <CrudDataTable v-model:column-visibility="columnVisibility" v-model:row-selection="rowSelection" :data="tableRows"
        :columns="uiColumns" :total="table.total.value" :loading="table.loading.value"
        :loading-more="table.loadingMore.value" :has-more="table.hasMore.value" selectable @load-more="table.loadMore()"
        @row-select="handleRowSelect" @row-contextmenu="handleRowContextmenu">
        <template #before-table>
          <RowContextMenu v-model:open="contextMenuOpen" :items="contextMenuItems" :x="contextMenuPosition.x"
            :y="contextMenuPosition.y" />
        </template>
        <template #actions-cell="{ row }">
          <USkeleton v-if="isSkeletonRow(row.original)" class="ml-auto h-4 w-8" />
          <UDropdownMenu v-else :content="{ align: 'end' }" :items="getRowActionItems(row.original)">
            <UButton icon="i-lucide-ellipsis-vertical" color="neutral" variant="ghost" size="sm" />
          </UDropdownMenu>
        </template>
        <template #empty>
          <CrudTableEmptyState :title="activeFilterCount ? 'Ничего не найдено' : 'Роли не найдены'" :description="activeFilterCount
            ? 'Нет ролей, соответствующих фильтрам. Измените условия поиска.'
            : 'Измените фильтры или создайте новую роль.'" :filtered="activeFilterCount > 0" :error="table.error.value"
            error-description="Не удалось загрузить роли. Проверьте подключение или повторите попытку позже."
            @clear-filters="resetFilters" @retry="table.refresh()" />
        </template>
      </CrudDataTable>
    </template>
  </UDashboardPanel>

  <AccessEntityDetailModal v-model:open="dialog.visible.value" :title="accessDialogTitle" kind="role"
    :mode="dialog.mode.value" :item="dialog.selected.value" :loading="permissionsLoading" :saving="saving"
    :read-only="dialog.readOnly.value" :editable="can('user-types', 'edit')" :permissions="permissions"
    :field-options="roleFieldOptions" @update:permissions="updatePermissions" @edit="dialog.startEdit()"
    @save="onSave" />

  <ConfirmDialog v-model:open="confirmDialog.open" :title="confirmDialog.title" :description="confirmDialog.description"
    :loading="deleting" confirm-color="error" confirm-label="Удалить" confirm-icon="i-lucide-trash-2"
    @confirm="confirmDialog.onConfirm" />
</template>
