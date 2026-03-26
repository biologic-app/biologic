<script setup lang="ts">
import { computed, h, onMounted, provide, reactive, ref, resolveComponent, watch } from 'vue'
import type { TableColumn as NuxtTableColumn } from '@nuxt/ui'
import type { TableRow } from '@nuxt/ui'
import type { TableFilters } from '@/shared/types/table'
import type { FormField } from '@/shared/types/form'
import type { Resource } from '@/shared/types/permissions'
import type { TableColumn } from '@/shared/types/table'
import CrudFormModal from '@/shared/components/CrudFormModal.vue'
import { useCrudDialog } from '@/shared/composables/useCrudDialog'
import { useOptimistic } from '@/shared/composables/useOptimistic'
import { usePermission } from '@/shared/composables/usePermission'
import { TABLE_PRESETS_KEY, useServerTable } from '@/shared/composables/useServerTable'
import { apiCreateRequest, apiReadListRequest, apiRequest, apiUpdateRequest, loadReferenceOptions } from '@/shared/api/client.api'
import { formatDateTime } from '@/shared/utils/format'
import { getValueByPath } from '@/shared/utils/object'

export interface CrudModuleConfig {
  resource: Resource
  title: string
  description: string
  endpoint: string
  include?: string
  presetKey: string
  pageId: string
  columns: TableColumn[]
  fields: FormField[]
  initialFilters: TableFilters
  pageSize?: number
}

type CrudRow = {
  id: string | number
  [key: string]: any
}

const props = defineProps<{
  config: CrudModuleConfig
}>()

const UButton = resolveComponent('UButton')
const UBadge = resolveComponent('UBadge')
const UTooltip = resolveComponent('UTooltip')

const toast = useToast()
const { can } = usePermission()
const table = useServerTable<CrudRow>(
  (params) =>
    apiReadListRequest<CrudRow>(props.config.endpoint, {
      method: 'GET',
      params: {
        ...params,
        include: props.config.include
      }
    }),
  {
    presetKey: props.config.presetKey,
    filters: props.config.initialFilters,
    initialPageSize: props.config.pageSize ?? 15
  }
)

provide(TABLE_PRESETS_KEY, {
  presets: table.presets,
  savePreset: table.savePreset,
  applyPreset: table.applyPreset,
  deletePreset: table.deletePreset
})

const dialog = useCrudDialog<CrudRow>(props.config.resource)
const optimistic = useOptimistic<CrudRow>()
const saving = ref(false)
const formFields = ref<FormField[]>([])
const presetName = ref('')
const pageSizeItems = [15, 30, 50, 100]
const filters = reactive<TableFilters>(JSON.parse(JSON.stringify(props.config.initialFilters)))

const syncFilters = () => {
  Object.entries(table.filters.value).forEach(([key, value]) => {
    filters[key] = { ...value }
  })
}

syncFilters()

watch(
  () => table.filters.value,
  () => {
    syncFilters()
  },
  { deep: true }
)

onMounted(async () => {
  await Promise.all([
    table.fetch(),
    Promise.all(
      props.config.fields
        .filter((field) => field.type === 'select' && field.options === undefined)
        .map(async (field) => {
          const endpoint = field.source
          if (!endpoint) {
            return
          }
          const options = await loadReferenceOptions(endpoint).catch(() => [])
          formFields.value = formFields.value.map((item) =>
            item.key === field.key ? { ...item, options } : item
          )
        })
    )
  ])
})

formFields.value = props.config.fields.map((field) => ({ ...field }))

const uiColumns = computed(() => {
  const actionColumn: NuxtTableColumn<CrudRow> = {
    id: 'actions',
    header: 'Действия',
    cell: ({ row }) => {
      const item = row.original as CrudRow

      const viewButton = h(UButton, {
        color: 'neutral',
        variant: 'ghost',
        icon: 'i-lucide-eye',
        onClick: () => dialog.openView(item)
      })

      const editButton = h(
        UTooltip as any,
        { text: can(props.config.resource, 'edit') ? 'Редактировать' : 'Нет прав' },
        () =>
          h(UButton, {
            color: 'neutral',
            variant: 'ghost',
            icon: can(props.config.resource, 'edit') ? 'i-lucide-pencil' : 'i-lucide-lock',
            disabled: !can(props.config.resource, 'edit'),
            onClick: () => dialog.openEdit(item)
          })
      )

      const deleteButton = h(
        UTooltip as any,
        { text: can(props.config.resource, 'delete') ? 'Удалить' : 'Нет прав' },
        () =>
          h(UButton, {
            color: 'error',
            variant: 'ghost',
            icon: can(props.config.resource, 'delete') ? 'i-lucide-trash-2' : 'i-lucide-lock',
            disabled: !can(props.config.resource, 'delete'),
            onClick: () => confirmDelete(item)
          })
      )

      return h('div', { class: 'flex items-center justify-end gap-1' }, [viewButton, editButton, deleteButton])
    },
    meta: { class: { td: 'w-[140px] text-right' } }
  }

  return [
    ...props.config.columns.map((column) => ({
      id: column.field,
      accessorKey: column.field,
      header: () =>
        h(UButton, {
          color: 'neutral',
          variant: 'ghost',
          label: column.header,
          disabled: !column.sortable,
          icon:
            table.sorting.value.field !== column.field
              ? 'i-lucide-arrow-up-down'
              : table.sorting.value.order === 1
                ? 'i-lucide-arrow-up-narrow-wide'
                : 'i-lucide-arrow-down-wide-narrow',
          class: column.sortable ? '-mx-2.5' : 'pointer-events-none -mx-2.5 opacity-100',
          onClick: () => column.sortable && table.setSort(column.field)
        }),
      cell: ({ row }: { row: TableRow<CrudRow> }) => {
        const rowItem = row.original as CrudRow
        if (column.body) {
          return column.body(rowItem)
        }

        const value = getValueByPath(rowItem, column.field)

        if (typeof value === 'boolean') {
          return h(
            UBadge,
            {
              color: value ? 'success' : 'neutral',
              variant: 'subtle'
            },
            () => (value ? 'Да' : 'Нет')
          )
        }

        if (typeof value === 'string' && /(at|date)$/i.test(column.field)) {
          return formatDateTime(value)
        }

        return value ?? '-'
      },
      meta: {
        class: {
          th: column.width ? `w-[${column.width}]` : undefined
        }
      }
    })),
    actionColumn
  ] as NuxtTableColumn<CrudRow>[]
})

const applyFilters = (debounceGlobal = false) => {
  table.updateFilters(JSON.parse(JSON.stringify(filters)), debounceGlobal)
}

const resetFilters = () => {
  Object.keys(props.config.initialFilters).forEach((key) => {
    filters[key] = { ...props.config.initialFilters[key] }
  })
  applyFilters()
}

const savePreset = () => {
  if (!presetName.value.trim()) {
    return
  }

  table.savePreset(presetName.value)
  toast.add({
    title: 'Пресет сохранён',
    color: 'success',
    icon: 'i-lucide-check'
  })
  presetName.value = ''
}

const onSave = async (payload: Record<string, any>) => {
  saving.value = true
  try {
    if (dialog.mode.value === 'create') {
      const response = await apiCreateRequest<CrudRow>(props.config.endpoint, {
        method: 'POST',
        body: payload
      })
      table.data.value = [response.data, ...table.data.value]
    } else if (dialog.selected.value?.id) {
      const optimisticRow = { ...dialog.selected.value, ...payload }
      const rollback = optimistic.updateItem(table.data, optimisticRow)
      try {
        const response = await apiUpdateRequest<CrudRow>(
          `${props.config.endpoint}/${dialog.selected.value.id}`,
          {
            method: 'PATCH',
            body: payload
          }
        )
        table.data.value = table.data.value.map((item) =>
          item.id === dialog.selected.value?.id ? response.data : item
        )
      } catch (error: any) {
        rollback()
        throw error
      }
    }

    dialog.close()
  } catch (error: any) {
    toast.add({
      title: 'Не удалось сохранить',
      description: error?.message || 'Попробуйте ещё раз',
      color: 'error',
      icon: 'i-lucide-circle-alert'
    })
  } finally {
    saving.value = false
  }
}

const confirmDelete = async (row: CrudRow) => {
  if (!window.confirm(`Удалить запись ${row.id}?`)) {
    return
  }

  const rollback = optimistic.removeItem(table.data, row.id)

  try {
    await apiRequest(`${props.config.endpoint}/${row.id}`, { method: 'DELETE' })
  } catch (error: any) {
    rollback()
    toast.add({
      title: 'Не удалось удалить',
      description: error?.message || 'Попробуйте ещё раз',
      color: 'error',
      icon: 'i-lucide-circle-alert'
    })
  }
}

const presetsItems = computed(() =>
  table.presets.value.map((preset) => ({
    label: preset.name,
    value: preset.name
  }))
)

const paginationPage = computed({
  get: () => table.pagination.value.page + 1,
  set: (value: number) => table.setPage(value - 1)
})

const createDisabled = computed(() => !can(props.config.resource, 'create'))
</script>

<template>
  <UDashboardPanel :id="config.pageId">
    <template #header>
      <UDashboardNavbar :title="config.title">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <UTooltip :text="createDisabled ? 'Нет прав на создание' : 'Создать запись'">
            <UButton
              :label="config.title.startsWith('Цели') ? 'Создать' : `Создать`"
              :icon="createDisabled ? 'i-lucide-lock' : 'i-lucide-plus'"
              :disabled="createDisabled"
              @click="dialog.openCreate()"
            />
          </UTooltip>
        </template>
      </UDashboardNavbar>

      <UDashboardToolbar>
        <template #left>
          <div class="flex w-full flex-col gap-3 lg:flex-row lg:items-center">
            <UInput
              v-model="filters.global.value"
              icon="i-lucide-search"
              class="w-full lg:w-80"
              placeholder="Глобальный поиск"
              @update:model-value="applyFilters(true)"
            />
            <UButton color="neutral" variant="outline" icon="i-lucide-refresh-cw" label="Обновить" @click="table.refresh()" />
          </div>
        </template>
        <template #right>
          <div class="flex flex-wrap items-center gap-2">
            <USelectMenu
              v-if="presetsItems.length"
              :items="presetsItems"
              value-key="value"
              label-key="label"
              placeholder="Применить пресет"
              class="w-48"
              @update:model-value="table.applyPreset(String($event))"
            />
            <UInput v-model="presetName" class="w-40" placeholder="Имя пресета" />
            <UButton color="neutral" variant="outline" icon="i-lucide-bookmark-plus" label="Сохранить пресет" @click="savePreset" />
          </div>
        </template>
      </UDashboardToolbar>
    </template>

    <template #body>
      <div class="grid gap-3 rounded-2xl border border-default bg-default p-4">
        <p class="text-sm text-toned">
          {{ config.description }}
        </p>

        <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          <div
            v-for="column in config.columns.filter((column) => column.filter)"
            :key="column.field"
            class="grid gap-2"
          >
            <label class="text-sm font-medium text-toned">
              {{ column.header }}
            </label>

            <div v-if="column.filter?.type === 'dateRange'" class="grid gap-2 sm:grid-cols-2">
              <UInput
                :model-value="filters[column.field].value?.[0] || ''"
                type="date"
                @update:model-value="
                  filters[column.field].value = [$event || null, filters[column.field].value?.[1] || null];
                  applyFilters()
                "
              />
              <UInput
                :model-value="filters[column.field].value?.[1] || ''"
                type="date"
                @update:model-value="
                  filters[column.field].value = [filters[column.field].value?.[0] || null, $event || null];
                  applyFilters()
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
                applyFilters()
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

        <div class="flex flex-wrap items-center justify-between gap-3">
          <UButton color="neutral" variant="ghost" icon="i-lucide-x" label="Сбросить фильтры" @click="resetFilters" />
          <div class="flex items-center gap-3 text-sm text-toned">
            <span>Всего: {{ table.total.value }}</span>
            <USelectMenu
              :model-value="table.pagination.value.size"
              :items="pageSizeItems"
              class="w-24"
              @update:model-value="table.setPageSize(Number($event))"
            />
          </div>
        </div>
      </div>

      <div class="rounded-2xl border border-default bg-default">
        <UTable
          :data="table.data.value"
          :columns="uiColumns"
          :loading="table.loading.value"
          sticky
          class="max-h-[calc(100vh-24rem)]"
          empty="Нет данных"
        />
      </div>

      <div class="flex justify-end">
        <UPagination
          v-model:page="paginationPage"
          :items-per-page="table.pagination.value.size"
          :total="table.total.value"
          show-edges
        />
      </div>
    </template>
  </UDashboardPanel>

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
