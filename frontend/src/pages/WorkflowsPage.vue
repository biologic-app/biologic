<script setup lang="ts">
// Страница «Рабочие процессы» — реестр шаблонов журналов (рабочих процессов)
// в таблице + конструктор процесса в полноэкранной модалке (как в направлениях).
import { computed, h, nextTick, onBeforeUnmount, onMounted, reactive, resolveComponent, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { TableColumn } from '@nuxt/ui'
import { useLocale } from '@/shared/composables/useLocale'
import { useTableColumnVisibility } from '@/shared/composables/useTableSettings'
import type { FormField } from '@/shared/types/form'
import ConfirmDialog from '@/shared/ui/ConfirmDialog.vue'
import CrudDataTable from '@/shared/ui/CrudDataTable.vue'
import CrudFilterControls from '@/shared/ui/CrudFilterControls.vue'
import CrudFilterModal from '@/shared/ui/CrudFilterModal.vue'
import CrudFormModal from '@/shared/ui/CrudFormModal.vue'
import CrudTableEmptyState from '@/shared/ui/CrudTableEmptyState.vue'
import RowContextMenu from '@/shared/ui/RowContextMenu.vue'
import type { DetailListItem } from '@/shared/ui/EntityDetailModalShell.vue'
import WorkflowDetailModal from '@/modules/journals/components/WorkflowDetailModal.vue'
import {
  createTemplate,
  deleteTemplate,
  getTemplate,
  getTemplates,
  initDemoData,
  renameTemplate,
} from '@/modules/journals/composables/useJournalStorage'
import { microbiologyStudy } from '@/modules/journals/data/microbiology-study'
import { patientIntake } from '@/modules/journals/data/patient-intake'
import { workflowCreation } from '@/modules/journals/data/workflow-creation'
import type { JournalSchema, JournalTemplate } from '@/modules/journals/types/journal'

const UButton = resolveComponent('UButton')

const toast = useToast()
const { t } = useI18n()
const { intlLocale } = useLocale()

const tableSettingsKey = 'table-settings:workflows:v1'
const columnVisibility = useTableColumnVisibility(tableSettingsKey)

interface WorkflowRow {
  id: string
  title: string
  versions: number
  currentVersion: number
  entries: number
  updatedAt: string
}

const templates = ref<JournalTemplate[]>([])
const search = ref('')

// Кратковременная подсветка недавно затронутой строки — как в «Направлениях».
const highlightId = ref<string | null>(null)
let highlightTimer: ReturnType<typeof setTimeout> | null = null
function highlightRow(id: string | null) {
  if (highlightTimer) {
    clearTimeout(highlightTimer)
    highlightTimer = null
  }
  highlightId.value = id
  if (!id) {
    return
  }
  highlightTimer = setTimeout(() => {
    highlightId.value = null
    highlightTimer = null
  }, 3500)
}

function refresh() {
  templates.value = getTemplates()
}

onMounted(() => {
  initDemoData([workflowCreation, patientIntake, microbiologyStudy])
  refresh()
})

onBeforeUnmount(() => {
  if (highlightTimer) {
    clearTimeout(highlightTimer)
  }
})

type SortableField = 'title' | 'versions' | 'currentVersion' | 'entries' | 'updatedAt'
const sortField = ref<SortableField>('updatedAt')
const sortOrder = ref<1 | -1>(-1)

function setSort(field: SortableField) {
  if (sortField.value === field) {
    sortOrder.value = sortOrder.value === 1 ? -1 : 1
    return
  }
  sortField.value = field
  sortOrder.value = 1
}

// ─── Фильтры — как в справочниках/направлениях (кнопка «Фильтр» + модалка) ─
interface WorkflowFilters {
  currentVersion: { min: number | undefined, max: number | undefined }
  updatedAt: { from: string | undefined, to: string | undefined }
}

function createEmptyFilters(): WorkflowFilters {
  return {
    currentVersion: { min: undefined, max: undefined },
    updatedAt: { from: undefined, to: undefined },
  }
}

const filters = reactive<WorkflowFilters>(createEmptyFilters())
const filterModalOpen = ref(false)

function resetFilters() {
  Object.assign(filters, createEmptyFilters())
}

const activeFilterCount = computed(() => {
  let count = 0
  if (filters.currentVersion.min !== undefined || filters.currentVersion.max !== undefined) {
    count += 1
  }
  if (filters.updatedAt.from !== undefined || filters.updatedAt.to !== undefined) {
    count += 1
  }
  return count
})

const rows = computed<WorkflowRow[]>(() => {
  const query = search.value.trim().toLowerCase()
  const filtered = templates.value
    .filter((template) => !query || template.title.toLowerCase().includes(query))
    .filter((template) => {
      const { min, max } = filters.currentVersion
      if (min !== undefined && template.currentVersion < min) return false
      if (max !== undefined && template.currentVersion > max) return false
      return true
    })
    .filter((template) => {
      const { from, to } = filters.updatedAt
      const updatedAt = template.updatedAt.slice(0, 10)
      if (from && updatedAt < from) return false
      if (to && updatedAt > to) return false
      return true
    })
    .map((template) => ({
      id: template.id,
      title: template.title,
      versions: template.versions.length,
      currentVersion: template.currentVersion,
      entries: template.versions.reduce((sum, version) => sum + version.entries.length, 0),
      updatedAt: template.updatedAt,
    }))

  const field = sortField.value
  const order = sortOrder.value
  return [...filtered].sort((a, b) => {
    const left = a[field]
    const right = b[field]
    if (left < right) return -1 * order
    if (left > right) return 1 * order
    return 0
  })
})

function sortHeader(field: SortableField, label: string) {
  return () =>
    h(UButton, {
      color: 'neutral',
      variant: 'ghost',
      label,
      icon:
        sortField.value !== field
          ? 'i-lucide-arrow-up-down'
          : sortOrder.value === 1
            ? 'i-lucide-arrow-up-narrow-wide'
            : 'i-lucide-arrow-down-wide-narrow',
      class: '-mx-2.5',
      onClick: () => setSort(field),
    })
}

const columns = computed<TableColumn<WorkflowRow>[]>(() => [
  { accessorKey: 'title', header: sortHeader('title', t('workflows.columns.title')) },
  { accessorKey: 'versions', header: sortHeader('versions', t('workflows.columns.versions')) },
  { accessorKey: 'currentVersion', header: sortHeader('currentVersion', t('workflows.columns.currentVersion')) },
  { accessorKey: 'entries', header: sortHeader('entries', t('workflows.columns.entries')) },
  { accessorKey: 'updatedAt', header: sortHeader('updatedAt', t('workflows.columns.updatedAt')) },
  {
    id: 'actions',
    header: t('workflows.columns.actions'),
    meta: { class: { td: 'w-auto min-w-[56px] text-right' } },
  },
])

const columnMenuItems = computed(() => {
  const entries: Array<{ key: string, label: string }> = [
    { key: 'title', label: t('workflows.columns.title') },
    { key: 'versions', label: t('workflows.columns.versions') },
    { key: 'currentVersion', label: t('workflows.columns.currentVersion') },
    { key: 'entries', label: t('workflows.columns.entries') },
    { key: 'updatedAt', label: t('workflows.columns.updatedAt') },
    { key: 'actions', label: t('workflows.columns.actions') },
  ]
  return entries.map(({ key, label }) => ({
    label,
    type: 'checkbox' as const,
    checked: columnVisibility.value[key] !== false,
    onUpdateChecked(checked: boolean) {
      columnVisibility.value = { ...columnVisibility.value, [key]: checked }
    },
    onSelect(event?: Event) {
      event?.preventDefault()
    },
  }))
})

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(intlLocale.value)
}

// ─── Конструктор (вкладка в карточке процесса) ─────────────────────────────
function openBuilder(id: string) {
  detailId.value = id
  detailActiveTab.value = 'builder'
  detailOpen.value = true
}

function onVersionSaved(version: number) {
  refresh()
  toast.add({ title: t('workflows.toasts.versionSaved', { version }), color: 'success', icon: 'i-lucide-check' })
}

// ─── Создание / переименование (единая форма, как в справочниках) ─────────
const formFields = computed<FormField[]>(() => [
  {
    key: 'title',
    label: t('workflows.form.titleLabel'),
    required: true,
    placeholder: t('workflows.form.titlePlaceholder'),
  },
])
const formModalOpen = ref(false)
const formMode = ref<'create' | 'edit'>('create')
const formItem = ref<Record<string, unknown> | null>(null)
const formEditId = ref<string | null>(null)

function openCreate() {
  formMode.value = 'create'
  formEditId.value = null
  formItem.value = { title: '' }
  formModalOpen.value = true
}

function openRename(row: WorkflowRow) {
  formMode.value = 'edit'
  formEditId.value = row.id
  formItem.value = { title: row.title }
  formModalOpen.value = true
}

function saveWorkflowForm(payload: Record<string, unknown>) {
  const title = String(payload.title ?? '').trim()
  if (!title) {
    return
  }

  if (formMode.value === 'edit' && formEditId.value) {
    renameTemplate(formEditId.value, title)
    formModalOpen.value = false
    refresh()
    toast.add({ title: t('workflows.toasts.renamed'), color: 'success', icon: 'i-lucide-check' })
    return
  }

  const schema: JournalSchema = {
    id: `template-${Date.now()}`,
    title,
    version: 1,
    nodes: [
      { id: 'start', type: 'start', position: { x: 0, y: 160 }, data: { label: 'Начало' } },
      { id: 'end', type: 'end', position: { x: 400, y: 160 }, data: { label: 'Конец' } },
    ],
    edges: [{ id: 'e-start-end', source: 'start', target: 'end' }],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  }
  const template = createTemplate(title, schema)
  formModalOpen.value = false
  refresh()
  toast.add({ title: t('workflows.toasts.created'), color: 'success', icon: 'i-lucide-check' })
  openBuilder(template.id)
}

// ─── Удаление ─────────────────────────────────────────────────────────────
const deleteOpen = ref(false)
const deleteRow = ref<WorkflowRow | null>(null)

function openDelete(row: WorkflowRow) {
  deleteRow.value = row
  deleteOpen.value = true
}

function confirmDelete() {
  if (!deleteRow.value) {
    return
  }
  deleteTemplate(deleteRow.value.id)
  deleteOpen.value = false
  deleteRow.value = null
  refresh()
  toast.add({ title: t('workflows.toasts.deleted'), color: 'success', icon: 'i-lucide-check' })
}

// ─── Множественный выбор строк — как во всех остальных таблицах ───────────
const rowSelection = ref<Record<string, boolean>>({})
const selectedRows = computed(() => rows.value.filter((row) => rowSelection.value[row.id]))

const bulkDeleteOpen = ref(false)

function openBulkDelete() {
  if (!selectedRows.value.length) {
    return
  }
  bulkDeleteOpen.value = true
}

function confirmBulkDelete() {
  const ids = selectedRows.value.map((row) => row.id)
  ids.forEach((id) => deleteTemplate(id))
  bulkDeleteOpen.value = false
  rowSelection.value = {}
  refresh()
  toast.add({ title: t('workflows.toasts.bulkDeleted', { count: ids.length }), color: 'success', icon: 'i-lucide-check' })
}

// ─── Карточка процесса — тот же каркас, что и у направлений ───────────────
const detailOpen = ref(false)
const detailId = ref<string | null>(null)
const detailActiveTab = ref('card')

const detailTemplate = computed(() => (detailId.value ? getTemplate(detailId.value) ?? null : null))

const listItems = computed<DetailListItem[]>(() =>
  rows.value.map((row) => ({
    id: row.id,
    title: row.title,
    date: formatDate(row.updatedAt),
    subtitle: t('workflows.detail.entriesCount', { count: row.entries }),
    badge: t('workflows.version', { version: row.currentVersion }),
    color: 'neutral',
  })),
)

function openDetail(id: string) {
  detailId.value = id
  detailActiveTab.value = 'card'
  detailOpen.value = true
}

function onDetailClose(open: boolean) {
  detailOpen.value = open
  if (!open) {
    const edited = detailId.value
    refresh()
    highlightRow(edited)
  }
}

function onDetailRename(template: JournalTemplate) {
  const row = rows.value.find((item) => item.id === template.id)
  if (row) {
    openRename(row)
  }
}

function onDetailDelete(template: JournalTemplate) {
  const row = rows.value.find((item) => item.id === template.id)
  if (row) {
    openDelete(row)
  }
}

// ─── Действия строки ──────────────────────────────────────────────────────
function rowActions(row: WorkflowRow) {
  return [
    [
      {
        label: t('workflows.actions.view'),
        icon: 'i-lucide-eye',
        onSelect: () => openDetail(row.id),
      },
      {
        label: t('workflows.actions.openBuilder'),
        icon: 'i-lucide-workflow',
        onSelect: () => openBuilder(row.id),
      },
      {
        label: t('workflows.actions.rename'),
        icon: 'i-lucide-pencil',
        onSelect: () => openRename(row),
      },
    ],
    [
      {
        label: t('workflows.actions.delete'),
        icon: 'i-lucide-trash-2',
        color: 'error' as const,
        onSelect: () => openDelete(row),
      },
    ],
  ]
}

// ─── Правый клик — контекстное меню строки (как во всех остальных таблицах) ─
const contextRow = ref<WorkflowRow | null>(null)
const contextMenuOpen = ref(false)
const contextMenuPosition = ref({ x: 0, y: 0 })

const contextMenuItems = computed(() => {
  if (!contextRow.value) {
    return []
  }
  return rowActions(contextRow.value).flatMap((group, index) =>
    index === 0 ? group : [{ type: 'separator' as const }, ...group],
  )
})

async function handleRowContextmenu(event: Event, row: { original: WorkflowRow }) {
  event.preventDefault()
  const mouseEvent = event as MouseEvent
  contextRow.value = row.original
  contextMenuOpen.value = false
  contextMenuPosition.value = { x: mouseEvent.clientX, y: mouseEvent.clientY }
  await nextTick()
  contextMenuOpen.value = true
}
</script>

<template>
  <UDashboardPanel id="workflows" :ui="{ body: 'min-h-0 overflow-hidden' }">
    <template #header>
      <UDashboardNavbar :title="t('workflows.title')">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <UButton
            :label="t('workflows.newProcess')"
            icon="i-lucide-plus"
            @click="openCreate"
          />
        </template>
      </UDashboardNavbar>

      <UDashboardToolbar>
        <template #left>
          <div class="flex w-full flex-col gap-3 lg:flex-row lg:items-center">
            <UInput
              v-model="search"
              icon="i-lucide-search"
              :placeholder="t('workflows.searchPlaceholder')"
              class="w-full lg:w-80"
            />
            <CrudFilterControls
              :active-count="activeFilterCount"
              @open="filterModalOpen = true"
              @clear="resetFilters"
            />
          </div>
        </template>
        <template #right>
          <div class="flex items-center gap-2">
            <UTooltip :text="t('workflows.refresh')">
              <UButton
                :label="t('workflows.refresh')"
                color="neutral"
                variant="subtle"
                icon="i-lucide-refresh-cw"
                @click="refresh"
              />
            </UTooltip>
            <UDropdownMenu :items="columnMenuItems" :content="{ align: 'end' }">
              <UTooltip :text="t('workflows.columnsTooltip')">
                <UButton
                  color="neutral"
                  variant="subtle"
                  trailing-icon="i-lucide-settings-2"
                />
              </UTooltip>
            </UDropdownMenu>
          </div>
        </template>
      </UDashboardToolbar>
    </template>

    <template #body>
      <div class="flex h-full min-h-0 w-full flex-col">
        <CrudFilterModal
          v-model:open="filterModalOpen"
          :active-count="activeFilterCount"
          @reset="resetFilters"
        >
          <div class="grid gap-3 sm:grid-cols-2">
            <div class="space-y-2">
              <p class="text-sm font-medium text-highlighted">
                {{ t('workflows.columns.currentVersion') }}
              </p>
              <div class="flex items-center gap-2">
                <UInput
                  v-model.number="filters.currentVersion.min"
                  type="number"
                  :min="1"
                  :placeholder="t('workflows.filters.versionFrom')"
                />
                <UInput
                  v-model.number="filters.currentVersion.max"
                  type="number"
                  :min="1"
                  :placeholder="t('workflows.filters.versionTo')"
                />
              </div>
            </div>
            <div class="space-y-2">
              <p class="text-sm font-medium text-highlighted">
                {{ t('workflows.columns.updatedAt') }}
              </p>
              <div class="flex items-center gap-2">
                <UInput
                  v-model="filters.updatedAt.from"
                  type="date"
                />
                <UInput
                  v-model="filters.updatedAt.to"
                  type="date"
                />
              </div>
            </div>
          </div>
        </CrudFilterModal>

        <CrudDataTable
          v-model:row-selection="rowSelection"
          v-model:column-visibility="columnVisibility"
          :data="rows"
          :columns="columns"
          :total="rows.length"
          :highlight-id="highlightId"
          selectable
          can-delete
          @row-contextmenu="handleRowContextmenu"
          @delete-selected="openBulkDelete"
        >
          <template #before-table>
            <RowContextMenu
              v-model:open="contextMenuOpen"
              :items="contextMenuItems"
              :x="contextMenuPosition.x"
              :y="contextMenuPosition.y"
            />
          </template>
          <template #title-cell="{ row }">
            <div class="flex items-center gap-2 font-medium text-highlighted">
              <UIcon name="i-lucide-file-text" class="size-4 text-dimmed" />
              {{ row.original.title }}
            </div>
          </template>
          <template #currentVersion-cell="{ row }">
            <UBadge
              color="neutral"
              variant="subtle"
              size="sm"
              :label="t('workflows.version', { version: row.original.currentVersion })"
            />
          </template>
          <template #updatedAt-cell="{ row }">
            {{ formatDate(row.original.updatedAt) }}
          </template>
          <template #actions-cell="{ row }">
            <UDropdownMenu :items="rowActions(row.original)" :content="{ align: 'end' }">
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
              :title="t('workflows.empty.title')"
              :description="t('workflows.empty.description')"
            />
          </template>
        </CrudDataTable>
      </div>
    </template>
  </UDashboardPanel>

  <!-- Карточка процесса — как у направлений: список слева + поля + история версий -->
  <WorkflowDetailModal
    v-model:active-tab="detailActiveTab"
    :open="detailOpen"
    :template="detailTemplate"
    :list-items="listItems"
    :selected-id="detailId"
    @update:open="onDetailClose"
    @select="(id) => (detailId = String(id))"
    @rename="onDetailRename"
    @delete="onDetailDelete"
    @version-saved="onVersionSaved"
  />

  <!-- Создание / переименование процесса — единая форма, как в справочниках -->
  <CrudFormModal
    :open="formModalOpen"
    :title="formMode === 'edit' ? t('workflows.form.renameTitle') : t('workflows.form.createTitle')"
    :fields="formFields"
    :item="formItem"
    :mode="formMode"
    @update:open="formModalOpen = $event"
    @save="saveWorkflowForm"
  />

  <!-- Удаление процесса -->
  <ConfirmDialog
    v-model:open="deleteOpen"
    :title="t('workflows.deleteDialog.title')"
    :description="t('workflows.deleteDialog.description', { title: deleteRow?.title ?? '' })"
    :confirm-label="t('workflows.deleteDialog.confirm')"
    confirm-color="error"
    confirm-icon="i-lucide-trash-2"
    @confirm="confirmDelete"
  />

  <!-- Массовое удаление выбранных процессов -->
  <ConfirmDialog
    v-model:open="bulkDeleteOpen"
    :title="t('workflows.bulkDeleteDialog.title')"
    :description="t('workflows.bulkDeleteDialog.description', { count: selectedRows.length })"
    :confirm-label="t('workflows.bulkDeleteDialog.confirm')"
    confirm-color="error"
    confirm-icon="i-lucide-trash-2"
    @confirm="confirmBulkDelete"
  />
</template>
