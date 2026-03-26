<script setup lang="ts">
import { computed, h, onMounted, reactive, ref, resolveComponent, watch } from 'vue'
import type { TableColumn as NuxtTableColumn } from '@nuxt/ui'
import { apiCreateRequest, apiReadListRequest, apiReadRequest, apiRequest, apiUpdateRequest } from '@/shared/api/client.api'
import PermissionEditor from '@/shared/components/PermissionEditor.vue'
import { useCrudDialog } from '@/shared/composables/useCrudDialog'
import { useOptimistic } from '@/shared/composables/useOptimistic'
import { usePermission } from '@/shared/composables/usePermission'
import { useServerTable } from '@/shared/composables/useServerTable'
import { summarizePermissions } from '@/shared/utils/permissions'
import type { Permission } from '@/shared/types/permissions'

const toast = useToast()
const { can } = usePermission()
type RoleRow = { id: string | number; [key: string]: any }

const dialog = useCrudDialog<RoleRow>('user-types')
const optimistic = useOptimistic<RoleRow>()
const saving = ref(false)
const permissionsLoading = ref(false)
const permissions = ref<Permission[]>([])
const activeTab = ref<'details' | 'permissions'>('details')
const formRef = ref<HTMLFormElement | null>(null)
const form = reactive({
  key: '',
  name: ''
})

const table = useServerTable<RoleRow>(
  (params) => apiReadListRequest<RoleRow>('/roles', { method: 'GET', params }),
  {
    presetKey: 'user-types',
    filters: {
      global: { value: '', matchMode: 'contains' },
      key: { value: '', matchMode: 'contains' },
      name: { value: '', matchMode: 'contains' },
      updated_at: { value: [null, null], matchMode: 'between' }
    }
  }
)

const filters = reactive(JSON.parse(JSON.stringify(table.filters.value)))

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
    activeTab.value = 'details'

    if (!isVisible) {
      permissions.value = []
      form.key = ''
      form.name = ''
      return
    }

    form.key = selected?.key || ''
    form.name = selected?.name || ''

    if (!selected?.id) {
      permissions.value = []
      return
    }

    permissionsLoading.value = true
    try {
      const response = await apiReadRequest<{ permissions: Permission[] }>(`/roles/${selected.id}/permissions`, {
        method: 'GET'
      }).catch(() =>
        apiReadRequest<{ permissions: Permission[] }>(`/user-types/${selected.id}/permissions`, {
          method: 'GET'
        })
      )
      permissions.value = response.data.permissions
    } catch (error: any) {
      toast.add({
        title: 'Не удалось загрузить права роли',
        description: error?.message || 'Попробуйте ещё раз',
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
      cell: ({ row }) => row.original.id
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
      cell: ({ row }) => row.original.key
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
      cell: ({ row }) => row.original.name
    },
    {
      id: 'summary',
      header: 'Права',
      cell: ({ row }) => {
        const summary = row.original.permissionsSummary || { view: 0, create: 0, edit: 0, delete: 0 }
        return h('div', { class: 'flex flex-wrap gap-1' }, [
          h(UBadge, { color: 'neutral', variant: 'subtle' }, () => `V ${summary.view}`),
          h(UBadge, { color: 'success', variant: 'subtle' }, () => `C ${summary.create}`),
          h(UBadge, { color: 'warning', variant: 'subtle' }, () => `E ${summary.edit}`),
          h(UBadge, { color: 'error', variant: 'subtle' }, () => `D ${summary.delete}`)
        ])
      }
    },
    {
      id: 'actions',
      header: 'Действия',
      cell: ({ row }) =>
        h('div', { class: 'flex justify-end gap-1' }, [
          h(UButton, {
            color: 'neutral',
            variant: 'ghost',
            icon: 'i-lucide-eye',
            onClick: () => dialog.openView(row.original)
          }),
          h(UButton, {
            color: 'neutral',
            variant: 'ghost',
            icon: can('user-types', 'edit') ? 'i-lucide-pencil' : 'i-lucide-lock',
            disabled: !can('user-types', 'edit'),
            onClick: () => dialog.openEdit(row.original)
          }),
          h(UButton, {
            color: 'error',
            variant: 'ghost',
            icon: can('user-types', 'delete') ? 'i-lucide-trash-2' : 'i-lucide-lock',
            disabled: !can('user-types', 'delete'),
            onClick: () => removeItem(row.original)
          })
        ])
    }
  ]
})

const tabItems = [
  { label: 'Данные', value: 'details' },
  { label: 'Права', value: 'permissions' }
]

const updatePermissions = (value: Permission[]) => {
  permissions.value = value
}

const applyFilters = (debounceGlobal = false) => {
  table.updateFilters(JSON.parse(JSON.stringify(filters)), debounceGlobal)
}

const removeItem = async (row: RoleRow) => {
  if (!window.confirm(`Удалить роль ${row.name}?`)) {
    return
  }

  const rollback = optimistic.removeItem(table.data, row.id)
  try {
    await apiRequest(`/roles/${row.id}`, { method: 'DELETE' })
  } catch (error: any) {
    rollback()
    toast.add({
      title: 'Не удалось удалить роль',
      description: error?.message || 'Попробуйте ещё раз',
      color: 'error'
    })
  }
}

const onSave = async () => {
  if (formRef.value && !formRef.value.reportValidity()) {
    return
  }

  saving.value = true
  try {
    if (dialog.mode.value === 'create') {
      const response = await apiCreateRequest<RoleRow>('/roles', {
        method: 'POST',
        body: { key: form.key, name: form.name }
      })

      if (permissions.value.length) {
        await apiRequest(`/roles/${response.data.id}/permissions`, {
          method: 'PUT',
          body: { permissions: permissions.value }
        }).catch(() =>
          apiRequest(`/user-types/${response.data.id}/permissions`, {
            method: 'PUT',
            body: { permissions: permissions.value }
          })
        )
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
        body: { key: form.key, name: form.name }
      })

      await apiRequest(`/roles/${selectedId}/permissions`, {
        method: 'PUT',
        body: { permissions: permissions.value }
      }).catch(() =>
        apiRequest(`/user-types/${selectedId}/permissions`, {
          method: 'PUT',
          body: { permissions: permissions.value }
        })
      )

      table.data.value = table.data.value.map((item) =>
        item.id === selectedId
          ? { ...response.data, permissionsSummary: summarizePermissions(permissions.value) }
          : item
      )
    }

    dialog.close()
  } catch (error: any) {
    toast.add({
      title: 'Не удалось сохранить роль',
      description: error?.message || 'Попробуйте ещё раз',
      color: 'error'
    })
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  table.fetch()
})
</script>

<template>
  <UDashboardPanel id="user-types">
    <template #header>
      <UDashboardNavbar title="Роли">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <UButton
            label="Создать роль"
            :icon="can('user-types', 'create') ? 'i-lucide-plus' : 'i-lucide-lock'"
            :disabled="!can('user-types', 'create')"
            @click="dialog.openCreate()"
          />
        </template>
      </UDashboardNavbar>

      <UDashboardToolbar>
        <template #left>
          <UInput
            v-model="filters.global.value"
            icon="i-lucide-search"
            class="w-full lg:w-80"
            placeholder="Поиск роли"
            @update:model-value="applyFilters(true)"
          />
        </template>
      </UDashboardToolbar>
    </template>

    <template #body>
      <div class="grid gap-3 md:grid-cols-3">
        <UInput v-model="filters.key.value" placeholder="Ключ" @update:model-value="applyFilters()" />
        <UInput v-model="filters.name.value" placeholder="Название" @update:model-value="applyFilters()" />
        <div class="grid gap-2 sm:grid-cols-2">
          <UInput
            :model-value="filters.updated_at.value?.[0] || ''"
            type="date"
            @update:model-value="
              filters.updated_at.value = [$event || null, filters.updated_at.value?.[1] || null];
              applyFilters()
            "
          />
          <UInput
            :model-value="filters.updated_at.value?.[1] || ''"
            type="date"
            @update:model-value="
              filters.updated_at.value = [filters.updated_at.value?.[0] || null, $event || null];
              applyFilters()
            "
          />
        </div>
      </div>

      <UTable :data="table.data.value" :columns="uiColumns" :loading="table.loading.value" sticky class="max-h-[calc(100vh-20rem)]" />

      <div class="flex justify-end">
        <UPagination
          :page="table.pagination.value.page + 1"
          :items-per-page="table.pagination.value.size"
          :total="table.total.value"
          show-edges
          @update:page="table.setPage($event - 1)"
        />
      </div>
    </template>
  </UDashboardPanel>

  <UModal
    :open="dialog.visible.value"
    :title="
      dialog.mode.value === 'create'
        ? 'Создать роль'
        : dialog.mode.value === 'edit'
          ? 'Редактировать роль'
          : 'Просмотр роли'
    "
    :ui="{ content: 'max-w-5xl' }"
    @update:open="dialog.visible.value = $event"
  >
    <template #body>
      <UTabs v-model="activeTab" :items="tabItems" :content="false" />

      <div v-if="activeTab === 'details'" class="mt-4">
        <form ref="formRef" class="grid gap-4 md:grid-cols-2" @submit.prevent="onSave">
          <div class="grid gap-2">
            <label class="text-sm font-medium text-toned">Ключ</label>
            <UInput v-model="form.key" required :disabled="dialog.readOnly.value" />
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium text-toned">Название</label>
            <UInput v-model="form.name" required :disabled="dialog.readOnly.value" />
          </div>
        </form>
      </div>

      <div v-else class="mt-4">
        <div v-if="permissionsLoading" class="py-8 text-center text-sm text-toned">
          Загрузка прав...
        </div>
        <PermissionEditor
          v-else
          mode="permissions"
          :permissions="permissions"
          :read-only="dialog.readOnly.value"
          @update:permissions="updatePermissions"
        />
      </div>
    </template>

    <template #footer>
      <div class="flex w-full items-center justify-end gap-3">
        <UButton color="neutral" variant="ghost" label="Закрыть" @click="dialog.close()" />
        <UButton v-if="!dialog.readOnly.value" :loading="saving" label="Сохранить" icon="i-lucide-save" @click="onSave" />
      </div>
    </template>
  </UModal>
</template>
