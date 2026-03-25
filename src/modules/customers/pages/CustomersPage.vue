<script setup lang="ts">
import { useTemplateRef, h, ref, computed, watch, resolveComponent } from 'vue'
import type { TableColumn } from '@nuxt/ui'
import type { TableMeta, Row } from '@tanstack/vue-table'
import { useFetch } from '@vueuse/core'
import { getPaginationRowModel, type Row as TRow } from '@tanstack/table-core'
import { useI18n } from 'vue-i18n'
import CustomersAddModal from '@/modules/customers/components/CustomersAddModal.vue'
import CustomersDeleteModal from '@/modules/customers/components/CustomersDeleteModal.vue'
import type { User } from '@/shared/types'

const UAvatar = resolveComponent('UAvatar')
const UButton = resolveComponent('UButton')
const UBadge = resolveComponent('UBadge')
const UDropdownMenu = resolveComponent('UDropdownMenu')
const UCheckbox = resolveComponent('UCheckbox')

const toast = useToast()
const table = useTemplateRef('table')
const { t } = useI18n()

const columnVisibility = ref()
const rowSelection = ref({ 1: true })

const { data, isFetching } = useFetch('https://dashboard-template.nuxt.dev/api/customers', { initialData: [] }).json<User[]>()

function sortableHeader(label: string, column: any) {
  const isSorted = column.getIsSorted()
  return h(UButton, {
    color: 'neutral',
    variant: 'ghost',
    label,
    icon: isSorted
      ? isSorted === 'asc' ? 'i-lucide-arrow-up-narrow-wide' : 'i-lucide-arrow-down-wide-narrow'
      : 'i-lucide-arrow-up-down',
    class: '-mx-2.5',
    onClick: () => column.toggleSorting(column.getIsSorted() === 'asc')
  })
}

function getStatusLabel(status: User['status']) {
  return t(`customers.${status}`)
}

function getColumnLabel(id: string) {
  const labels: Record<string, string> = {
    id: t('customers.fields.id'),
    name: t('customers.fields.name'),
    email: t('customers.fields.email'),
    location: t('customers.fields.location'),
    status: t('customers.fields.status')
  }

  return labels[id] ?? id
}

function getRowItems(row: TRow<User>) {
  return [
    { type: 'label', label: t('customers.actions') },
    {
      label: t('customers.copyId'),
      icon: 'i-lucide-copy',
      onSelect() {
        navigator.clipboard.writeText(row.original.id.toString())
        toast.add({ title: t('customers.copiedTitle'), description: t('customers.copiedDescription') })
      }
    },
    { type: 'separator' },
    { label: t('customers.viewCard'), icon: 'i-lucide-list' },
    { label: t('customers.analysisHistory'), icon: 'i-lucide-flask-conical' },
    { type: 'separator' },
    {
      label: t('customers.deletePatient'),
      icon: 'i-lucide-trash',
      color: 'error',
      onSelect() {
        toast.add({ title: t('customers.deletedTitle'), color: 'error' })
      }
    }
  ]
}

const columns = computed<TableColumn<User>[]>(() => [
  {
    id: 'select',
    enableSorting: false,
    enableHiding: false,
    header: ({ table: currentTable }) =>
      h(UCheckbox, {
        modelValue: currentTable.getIsSomePageRowsSelected() ? 'indeterminate' : currentTable.getIsAllPageRowsSelected(),
        'onUpdate:modelValue': (value: boolean | 'indeterminate') => currentTable.toggleAllPageRowsSelected(!!value),
        ariaLabel: t('customers.selectAll')
      }),
    cell: ({ row }) =>
      h(UCheckbox, {
        modelValue: row.getIsSelected(),
        'onUpdate:modelValue': (value: boolean | 'indeterminate') => row.toggleSelected(!!value),
        ariaLabel: t('customers.selectRow')
      })
  },
  {
    accessorKey: 'id',
    header: ({ column }) => sortableHeader(t('customers.fields.id'), column)
  },
  {
    accessorKey: 'name',
    header: ({ column }) => sortableHeader(t('customers.fields.name'), column),
    cell: ({ row }) =>
      h('div', { class: 'flex items-center gap-2' }, [
        h(UAvatar, { ...row.original.avatar, size: 'sm' }),
        h('div', undefined, [
          h('p', { class: 'font-medium text-highlighted text-sm leading-tight' }, row.original.name),
          h('p', { class: 'text-xs text-muted' }, `@${row.original.name}`)
        ])
      ])
  },
  {
    accessorKey: 'email',
    header: ({ column }) => sortableHeader(t('customers.fields.email'), column),
    meta: { class: { td: 'text-sm text-muted' } }
  },
  {
    accessorKey: 'location',
    header: ({ column }) => sortableHeader(t('customers.fields.location'), column),
    cell: ({ row }) => h('span', { class: 'text-sm' }, row.original.location)
  },
  {
    accessorKey: 'status',
    header: ({ column }) => sortableHeader(t('customers.fields.status'), column),
    filterFn: 'equals',
    cell: ({ row }) => {
      const status = row.original.status
      const color = {
        subscribed: 'success' as const,
        unsubscribed: 'error' as const,
        bounced: 'warning' as const
      }[status]
      return h(UBadge, { class: 'capitalize', variant: 'subtle', color }, () => getStatusLabel(status))
    }
  },
  {
    id: 'actions',
    enableHiding: false,
    meta: { class: { td: 'text-right' } },
    cell: ({ row }) =>
      h('div', { class: 'text-right' },
        h(UDropdownMenu, {
          content: { align: 'end' },
          items: getRowItems(row)
        }, () => h(UButton, {
          icon: 'i-lucide-ellipsis-vertical',
          color: 'neutral',
          variant: 'ghost',
          class: 'ml-auto'
        }))
      )
  }
])

const tableMeta: TableMeta<User> = {
  class: {
    tr: (row: Row<User>) => {
      const statusClass = {
        subscribed: 'bg-success/15 dark:bg-success/15 hover:bg-success/10',
        unsubscribed: 'bg-error/15 dark:bg-error/15 hover:bg-error/10',
        bounced: 'bg-warning/15 dark:bg-warning/15 hover:bg-warning/10'
      }[row.original.status] ?? ''

      return row.getIsSelected() ? `${statusClass}` : statusClass
    }
  }
}

const statusFilter = ref('all')
const statusOptions = computed(() => [
  { label: t('customers.allStatuses'), value: 'all' },
  { label: t('customers.subscribed'), value: 'subscribed' },
  { label: t('customers.unsubscribed'), value: 'unsubscribed' },
  { label: t('customers.bounced'), value: 'bounced' }
])

watch(() => statusFilter.value, (newValue) => {
  const column = table.value?.tableApi?.getColumn('status')
  if (!column) {
    return
  }
  column.setFilterValue(newValue === 'all' ? undefined : newValue)
})

const pagination = ref({ pageIndex: 0, pageSize: 500 })
</script>

<template>
  <UDashboardPanel id="customers">
    <template #header>
      <UDashboardNavbar :title="t('customers.title')">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <CustomersAddModal />
        </template>
      </UDashboardNavbar>
    </template>

    <template #body>
      <div class="flex flex-wrap items-center justify-between gap-1.5">
        <div class="flex flex-wrap items-center gap-1.5">
          <USelect
            v-model="statusFilter"
            :items="statusOptions"
            :placeholder="t('common.status')"
            class="min-w-28"
          />
        </div>

        <div class="flex items-center gap-1.5">
          <CustomersDeleteModal :count="table?.tableApi?.getFilteredSelectedRowModel().rows.length">
            <UButton
              v-if="table?.tableApi?.getFilteredSelectedRowModel().rows.length"
              :label="t('common.delete')"
              color="error"
              variant="subtle"
              icon="i-lucide-trash"
            >
              <template #trailing>
                <UKbd>{{ table?.tableApi?.getFilteredSelectedRowModel().rows.length }}</UKbd>
              </template>
            </UButton>
          </CustomersDeleteModal>

          <UDropdownMenu
            :items="table?.tableApi?.getAllColumns()
              .filter((column: any) => column.getCanHide())
              .map((column: any) => ({
                label: getColumnLabel(column.id),
                type: 'checkbox' as const,
                checked: column.getIsVisible(),
                onUpdateChecked(checked: boolean) { column.toggleVisibility(!!checked) },
                onSelect(event?: Event) { event?.preventDefault() }
              }))"
            :content="{ align: 'end' }"
          >
            <UButton :label="t('customers.columns')" color="neutral" variant="outline" trailing-icon="i-lucide-settings-2" />
          </UDropdownMenu>
        </div>
      </div>

      <UTable
        ref="table"
        v-model:column-visibility="columnVisibility"
        v-model:row-selection="rowSelection"
        v-model:pagination="pagination"
        :pagination-options="{ getPaginationRowModel: getPaginationRowModel() }"
        :data="data ?? []"
        :columns="columns"
        :meta="tableMeta"
        :loading="isFetching"
        class="shrink-0"
        sticky
      />
    </template>
  </UDashboardPanel>
</template>
