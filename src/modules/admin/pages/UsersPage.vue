<script setup lang="ts">
import { computed, h, onMounted, reactive, ref, resolveComponent, watch } from 'vue'
import type { TableColumn as NuxtTableColumn } from '@nuxt/ui'
import { apiCreateRequest, apiReadListRequest, apiReadRequest, apiRequest, apiUpdateRequest, loadReferenceOptions } from '@/shared/api/client.api'
import PermissionEditor from '@/shared/components/PermissionEditor.vue'
import { useCrudDialog } from '@/shared/composables/useCrudDialog'
import { useOptimistic } from '@/shared/composables/useOptimistic'
import { usePermission } from '@/shared/composables/usePermission'
import { useServerTable } from '@/shared/composables/useServerTable'
import type { Permission, PermissionOverride } from '@/shared/types/permissions'
import { useAuthStore } from '@/modules/auth/auth.store'

const toast = useToast()
const auth = useAuthStore()
const { can } = usePermission()
type UserRow = { id: string | number; [key: string]: any }

const dialog = useCrudDialog<UserRow>('users')
const optimistic = useOptimistic<UserRow>()
const saving = ref(false)
const activeTab = ref<'details' | 'permissions'>('details')
const rolePermissions = ref<Permission[]>([])
const overrides = ref<PermissionOverride[]>([])
const permissionsLoading = ref(false)
const roleOptions = ref<Array<{ label: string; value: string | number | boolean | null }>>([])
const labOptions = ref<Array<{ label: string; value: string | number | boolean | null }>>([])
const formRef = ref<HTMLFormElement | null>(null)
const form = reactive({
  username: '',
  code: '',
  first_name: '',
  last_name: '',
  patronymic: '',
  role_id: '',
  lab_id: null as string | number | boolean | null,
  is_registrar: false,
  is_lab_head: false,
  is_branch_head: false,
  password_hash: ''
})

const table = useServerTable<UserRow>(
  (params) =>
    apiReadListRequest<UserRow>('/users', {
      method: 'GET',
      params: {
        ...params,
        include: 'role,lab'
      }
    }),
  {
    presetKey: 'users',
    filters: {
      global: { value: '', matchMode: 'contains' },
      username: { value: '', matchMode: 'contains' },
      code: { value: '', matchMode: 'contains' },
      first_name: { value: '', matchMode: 'contains' },
      last_name: { value: '', matchMode: 'contains' },
      'role.name': { value: '', matchMode: 'contains' },
      'lab.name': { value: '', matchMode: 'contains' },
      is_registrar: { value: [], matchMode: 'in' },
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
      rolePermissions.value = []
      overrides.value = []
      form.username = ''
      form.code = ''
      form.first_name = ''
      form.last_name = ''
      form.patronymic = ''
      form.role_id = ''
      form.lab_id = null
      form.is_registrar = false
      form.is_lab_head = false
      form.is_branch_head = false
      form.password_hash = ''
      return
    }

    form.username = selected?.username || ''
    form.code = selected?.code || ''
    form.first_name = selected?.first_name || ''
    form.last_name = selected?.last_name || ''
    form.patronymic = selected?.patronymic || ''
    form.role_id = selected?.role_id || ''
    form.lab_id = selected?.lab_id || null
    form.is_registrar = Boolean(selected?.is_registrar)
    form.is_lab_head = Boolean(selected?.is_lab_head)
    form.is_branch_head = Boolean(selected?.is_branch_head)
    form.password_hash = ''

    if (!selected?.id) {
      rolePermissions.value = []
      overrides.value = []
      return
    }

    permissionsLoading.value = true
    try {
      const response = await apiReadRequest<{ rolePermissions: Permission[]; overrides: PermissionOverride[] }>(
        `/users/${selected.id}/permissions`,
        {
          method: 'GET'
        }
      )
      rolePermissions.value = response.data.rolePermissions
      overrides.value = response.data.overrides
    } catch (error: any) {
      toast.add({
        title: 'Не удалось загрузить права пользователя',
        description: error?.message || 'Попробуйте ещё раз',
        color: 'error'
      })
    } finally {
      permissionsLoading.value = false
    }
  },
  { immediate: true }
)

const uiColumns = computed<NuxtTableColumn<UserRow>[]>(() => {
  const UButton = resolveComponent('UButton')
  const UBadge = resolveComponent('UBadge')

  return [
    {
      accessorKey: 'id',
      header: 'ID',
      cell: ({ row }) => row.original.id
    },
    {
      accessorKey: 'username',
      header: () =>
        h(UButton, {
          color: 'neutral',
          variant: 'ghost',
          label: 'Логин',
          icon:
            table.sorting.value.field !== 'username'
              ? 'i-lucide-arrow-up-down'
              : table.sorting.value.order === 1
                ? 'i-lucide-arrow-up-narrow-wide'
                : 'i-lucide-arrow-down-wide-narrow',
          onClick: () => table.setSort('username')
        }),
      cell: ({ row }) => row.original.username
    },
    {
      accessorKey: 'first_name',
      header: 'Имя',
      cell: ({ row }) => row.original.first_name || '-'
    },
    {
      accessorKey: 'last_name',
      header: 'Фамилия / Отчество',
      cell: ({ row }) => [row.original.last_name, row.original.patronymic].filter(Boolean).join(' ') || '-'
    },
    {
      accessorKey: 'role.name',
      header: 'Роль',
      cell: ({ row }) => row.original.role?.name || '-'
    },
    {
      accessorKey: 'lab.name',
      header: 'Лаборатория',
      cell: ({ row }) => row.original.lab?.name || '-'
    },
    {
      accessorKey: 'is_registrar',
      header: 'Регистратор',
      cell: ({ row }) =>
        h(UBadge, { color: row.original.is_registrar ? 'success' : 'neutral', variant: 'subtle' }, () =>
          row.original.is_registrar ? 'Да' : 'Нет'
        )
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
            icon: can('users', 'edit') ? 'i-lucide-pencil' : 'i-lucide-lock',
            disabled: !can('users', 'edit'),
            onClick: () => dialog.openEdit(row.original)
          }),
          h(UButton, {
            color: 'error',
            variant: 'ghost',
            icon: can('users', 'delete') ? 'i-lucide-trash-2' : 'i-lucide-lock',
            disabled: !can('users', 'delete'),
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

const updateOverrides = (value: PermissionOverride[]) => {
  overrides.value = value
}

const applyFilters = (debounceGlobal = false) => {
  table.updateFilters(JSON.parse(JSON.stringify(filters)), debounceGlobal)
}

const removeItem = async (row: UserRow) => {
  if (!window.confirm(`Удалить пользователя ${row.username}?`)) {
    return
  }

  const rollback = optimistic.removeItem(table.data, row.id)
  try {
    await apiRequest(`/users/${row.id}`, { method: 'DELETE' })
  } catch (error: any) {
    rollback()
    toast.add({
      title: 'Не удалось удалить пользователя',
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
    const payload: Record<string, any> = {
      username: form.username,
      code: form.code || null,
      first_name: form.first_name || null,
      last_name: form.last_name || null,
      patronymic: form.patronymic || null,
      role_id: form.role_id || null,
      lab_id: form.lab_id || null,
      is_registrar: form.is_registrar,
      is_lab_head: form.is_lab_head,
      is_branch_head: form.is_branch_head
    }

    if (form.password_hash.trim()) {
      payload.password_hash = form.password_hash
    }

    if (dialog.mode.value === 'create') {
      const response = await apiCreateRequest<UserRow>('/users', {
        method: 'POST',
        body: payload
      })

      if (overrides.value.length) {
        await apiRequest(`/users/${response.data.id}/permissions`, {
          method: 'PUT',
          body: { overrides: overrides.value }
        })
      }

      table.data.value = [{ ...response.data, overridesCount: overrides.value.length }, ...table.data.value]
    } else if (dialog.selected.value?.id) {
      const selectedId = dialog.selected.value.id
      const response = await apiUpdateRequest<UserRow>(`/users/${selectedId}`, {
        method: 'PATCH',
        body: payload
      })

      await apiRequest(`/users/${selectedId}/permissions`, {
        method: 'PUT',
        body: { overrides: overrides.value }
      })

      table.data.value = table.data.value.map((item) =>
        item.id === selectedId ? { ...response.data, overridesCount: overrides.value.length } : item
      )

      if (String(auth.user?.id) === String(selectedId)) {
        await auth.restoreSession()
      }
    }

    dialog.close()
  } catch (error: any) {
    toast.add({
      title: 'Не удалось сохранить пользователя',
      description: error?.message || 'Попробуйте ещё раз',
      color: 'error'
    })
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  const [roles, labs] = await Promise.all([
    loadReferenceOptions('/roles').catch(() => []),
    loadReferenceOptions('/labs').catch(() => [])
  ])
  roleOptions.value = roles
  labOptions.value = labs
  await table.fetch()
})
</script>

<template>
  <UDashboardPanel id="users">
    <template #header>
      <UDashboardNavbar title="Пользователи">
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
        <template #left>
          <UInput
            v-model="filters.global.value"
            icon="i-lucide-search"
            class="w-full lg:w-80"
            placeholder="Поиск пользователя"
            @update:model-value="applyFilters(true)"
          />
        </template>
      </UDashboardToolbar>
    </template>

    <template #body>
      <div class="grid gap-3 lg:grid-cols-4">
        <UInput v-model="filters.username.value" placeholder="Логин" @update:model-value="applyFilters()" />
        <UInput v-model="filters.code.value" placeholder="Код" @update:model-value="applyFilters()" />
        <UInput v-model="filters['role.name'].value" placeholder="Роль" @update:model-value="applyFilters()" />
        <UInput v-model="filters['lab.name'].value" placeholder="Лаборатория" @update:model-value="applyFilters()" />
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
        ? 'Создать пользователя'
        : dialog.mode.value === 'edit'
          ? 'Редактировать пользователя'
          : 'Просмотр пользователя'
    "
    :ui="{ content: 'max-w-6xl' }"
    @update:open="dialog.visible.value = $event"
  >
    <template #body>
      <UTabs v-model="activeTab" :items="tabItems" :content="false" />

      <div v-if="activeTab === 'details'" class="mt-4">
        <form ref="formRef" class="grid gap-4 md:grid-cols-2" @submit.prevent="onSave">
          <div class="grid gap-2">
            <label class="text-sm font-medium text-toned">Логин</label>
            <UInput v-model="form.username" required :disabled="dialog.readOnly.value" />
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium text-toned">Код</label>
            <UInput v-model="form.code" :disabled="dialog.readOnly.value" />
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium text-toned">Имя</label>
            <UInput v-model="form.first_name" :disabled="dialog.readOnly.value" />
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium text-toned">Фамилия</label>
            <UInput v-model="form.last_name" :disabled="dialog.readOnly.value" />
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium text-toned">Отчество</label>
            <UInput v-model="form.patronymic" :disabled="dialog.readOnly.value" />
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium text-toned">Роль</label>
            <USelectMenu
              v-model="form.role_id"
              :items="roleOptions"
              value-key="value"
              label-key="label"
              :disabled="dialog.readOnly.value"
            />
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium text-toned">Лаборатория</label>
            <USelectMenu
              v-model="form.lab_id"
              :items="labOptions"
              value-key="value"
              label-key="label"
              :disabled="dialog.readOnly.value"
              clear
            />
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium text-toned">Пароль</label>
            <UInput
              v-model="form.password_hash"
              type="password"
              :required="dialog.mode.value === 'create'"
              :disabled="dialog.readOnly.value"
            />
          </div>
          <div class="grid gap-3 md:col-span-2 lg:grid-cols-3">
            <UCheckbox v-model="form.is_registrar" label="Регистратор" :disabled="dialog.readOnly.value" />
            <UCheckbox v-model="form.is_lab_head" label="Руководитель лаборатории" :disabled="dialog.readOnly.value" />
            <UCheckbox v-model="form.is_branch_head" label="Руководитель филиала" :disabled="dialog.readOnly.value" />
          </div>
        </form>
      </div>

      <div v-else class="mt-4">
        <div v-if="permissionsLoading" class="py-8 text-center text-sm text-toned">
          Загрузка прав...
        </div>
        <PermissionEditor
          v-else
          mode="overrides"
          :role-permissions="rolePermissions"
          :overrides="overrides"
          :read-only="dialog.readOnly.value"
          @update:overrides="updateOverrides"
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
