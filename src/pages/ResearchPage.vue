<script setup lang="ts">
import { h, computed, nextTick, reactive, ref, resolveComponent, watch, onMounted } from 'vue'
import type { DropdownMenuItem, TableColumn } from '@nuxt/ui'
import { useI18n } from 'vue-i18n'
import { useResearchSamples } from '@/modules/research/composables/useResearchSamples'
import { useServerTable } from '@/shared/composables/useServerTable'
import { usePersistedTableSetting, useTableColumnVisibility } from '@/shared/composables/useTableSettings'
import CrudDataTable from '@/shared/ui/CrudDataTable.vue'
import CrudSearchControl from '@/shared/ui/CrudSearchControl.vue'
import CrudFilterControls from '@/shared/ui/CrudFilterControls.vue'
import CrudTableEmptyState from '@/shared/ui/CrudTableEmptyState.vue'
import RowContextMenu from '@/shared/ui/RowContextMenu.vue'
import {
  borderedCrudTableUi,
  createSkeletonRows,
  isSkeletonRow,
  renderSkeletonCell,
} from '@/shared/ui/table'
import { statusColors } from '@/shared/constants/research'
import ResearchDetailModal from '@/modules/research/components/ResearchDetailModal.vue'
import type { ResearchSample, ResearchStatus } from '@/shared/types'

type SortKey = 'updatedAt' | 'registeredAt' | 'code'
type QuickFilter = 'all' | 'active' | 'completed' | 'urgent'

const { t } = useI18n()
const { samples } = useResearchSamples()
const toast = useToast()
const tableSettingsKey = 'table-settings:research'

const searchQuery = usePersistedTableSetting(tableSettingsKey, 'query', '')
const quickFilter = ref<QuickFilter>('all')
const sortKey = ref<SortKey>('updatedAt')
const selectedSample = ref<ResearchSample | null>(null)
const detailOpen = ref(false)
const closeModalOpen = ref(false)
const resultModalOpen = ref(false)
const assignModalOpen = ref(false)
const columnVisibility = useTableColumnVisibility(tableSettingsKey, { actions: false })
const contextRow = ref<ResearchSample | null>(null)
const contextMenuOpen = ref(false)
const contextMenuPosition = ref({ x: 0, y: 0 })
const skeletonRows = createSkeletonRows<ResearchSample>(17)

const resultForm = reactive({ status: 'inProgress' as ResearchStatus, completed: false, note: '', recommendations: '', issuedAt: '' })
const assignForm = reactive({ indicator: '', lab: '' })
const closeForm = reactive({ verdict: '' })

const activeStatuses: ResearchStatus[] = ['registered', 'inProgress', 'review']

const filteredSamples = computed<ResearchSample[]>(() => {
  const q = searchQuery.value.trim().toLocaleLowerCase()
  const list: ResearchSample[] = []
  for (const s of samples.value as ResearchSample[]) {
    const mqf = quickFilter.value === 'all'
      || (quickFilter.value === 'active' && activeStatuses.includes(s.status))
      || (quickFilter.value === 'completed' && s.status === 'completed')
      || (quickFilter.value === 'urgent' && s.priority === 'urgent')
    const mq = !q || s.code.toLocaleLowerCase().includes(q) || s.patient.name.toLocaleLowerCase().includes(q)
      || s.material.toLocaleLowerCase().includes(q) || s.direction.toLocaleLowerCase().includes(q)
    if (mqf && mq) list.push(s)
  }
  return [...list].sort((a, b) => {
    if (sortKey.value === 'code') return a.code.localeCompare(b.code)
    const da = sortKey.value === 'registeredAt' ? a.registeredAt : a.updatedAt
    const db = sortKey.value === 'registeredAt' ? b.registeredAt : b.updatedAt
    return new Date(db).getTime() - new Date(da).getTime()
  })
})

const getResearchSortValue = (sample: ResearchSample, field: string) => {
  if (field === 'patient.name') return sample.patient.name;
  return sample[field as keyof ResearchSample];
}

const table = useServerTable<ResearchSample>(
  async (params) => {
    const offset = Number(params.cursor ?? params.offset ?? 0)
    const limit = Number(params.limit ?? 30)
    const field = String(params.sort_by || '')
    const list = field
      ? [...filteredSamples.value].sort((a, b) => {
        const order = params.sort_order === 'desc' ? -1 : 1
        const left = getResearchSortValue(a, field)
        const right = getResearchSortValue(b, field)
        return String(left ?? '').localeCompare(String(right ?? ''), 'ru') * order
      })
      : filteredSamples.value
    const nextOffset = offset + limit
    const hasMore = nextOffset < list.length
    return {
      items: list.slice(offset, offset + limit),
      meta: {
        timestamp: new Date().toISOString(),
        requestId: 'research-local',
        version: 'mock',
        includesRequested: [],
        includesApplied: [],
        includesAllowed: [],
        total: list.length,
        offset,
        limit,
        nextCursor: hasMore ? String(nextOffset) : null,
        hasMore,
      },
    }
  },
  { mode: 'infinite', initialPageSize: 30, settingsKey: tableSettingsKey }
)

const tableRows = computed(() =>
  table.loading.value ? skeletonRows : table.data.value,
)

// Initial fetch in onMounted so skeleton renders first
onMounted(() => { table.fetch() })

watch([searchQuery, quickFilter, sortKey], () => { table.refresh() })

const UBadge = resolveComponent('UBadge')
const UButton = resolveComponent('UButton')

function sortableHeader(label: string, field: string) {
  return h(UButton, {
    color: 'neutral',
    variant: 'ghost',
    label,
    icon:
      table.sorting.value.field !== field
        ? 'i-lucide-arrow-up-down'
        : table.sorting.value.order === 1
          ? 'i-lucide-arrow-up-narrow-wide'
          : 'i-lucide-arrow-down-wide-narrow',
    class: '-mx-2.5',
    onClick: () => table.setSort(field),
  })
}

const uiColumns = computed<TableColumn<ResearchSample>[]>(() => [
  { accessorKey: 'code', header: () => sortableHeader('Код', 'code'), cell: ({ row }) => isSkeletonRow(row.original) ? renderSkeletonCell('code', 0) : h('span', { class: 'font-semibold text-highlighted' }, row.original.code) },
  { accessorKey: 'patient.name', header: () => sortableHeader('Пациент', 'patient.name'), cell: ({ row }) => isSkeletonRow(row.original) ? renderSkeletonCell('patient.name', 1) : row.original.patient.name },
  { accessorKey: 'material', header: () => sortableHeader('Материал', 'material'), cell: ({ row }) => isSkeletonRow(row.original) ? renderSkeletonCell('material', 2) : row.original.material },
  { accessorKey: 'direction', header: () => sortableHeader('Направление', 'direction'), cell: ({ row }) => isSkeletonRow(row.original) ? renderSkeletonCell('direction', 3) : row.original.direction },
  { accessorKey: 'status', header: () => sortableHeader('Статус', 'status'), cell: ({ row }) => isSkeletonRow(row.original) ? renderSkeletonCell('status', 4) : h(UBadge, { color: statusColors[row.original.status], variant: 'subtle', label: t(`research.status.${row.original.status}`) }) },
  { accessorKey: 'priority', header: () => sortableHeader('Приоритет', 'priority'), cell: ({ row }) => isSkeletonRow(row.original) ? renderSkeletonCell('priority', 5) : h(UBadge, { color: row.original.priority === 'urgent' ? 'warning' : 'neutral', variant: 'subtle', label: t(`research.priority.${row.original.priority}`) }) },
  { accessorKey: 'updatedAt', header: () => sortableHeader('Обновлено', 'updatedAt'), cell: ({ row }) => isSkeletonRow(row.original) ? renderSkeletonCell('updatedAt', 6) : new Date(row.original.updatedAt).toLocaleDateString('ru') },
  { id: 'actions', header: 'Действия', meta: { class: { td: 'w-auto min-w-[56px] text-right' } } },
])

// ---- Action handlers ----
function openDetail(sample: ResearchSample) { selectedSample.value = sample; detailOpen.value = true }
function clearFilters() { searchQuery.value = ''; quickFilter.value = 'all' }

function handleResearchAction(action: string) {
  if (action === 'close-sample') { closeModalOpen.value = true; return }
  if (action === 'assign-test') { assignModalOpen.value = true; return }
  if (selectedSample.value) {
    resultForm.status = selectedSample.value.status
    resultForm.completed = selectedSample.value.status === 'completed'
    resultForm.note = selectedSample.value.comment
    resultForm.recommendations = ''
    resultForm.issuedAt = new Date().toISOString().slice(0, 16)
  }
  resultModalOpen.value = true
}
function closeSample() {
  if (!selectedSample.value) return
  selectedSample.value.status = 'completed'
  selectedSample.value.history.push({ id: Date.now(), status: 'completed', date: new Date().toISOString(), actor: "Специалист лаборатории", note: 'Образец закрыт.' })
  closeModalOpen.value = false
  toast.add({ title: 'Образец закрыт', color: 'success' })
}
function completeTest() {
  if (!selectedSample.value) return
  selectedSample.value.status = resultForm.completed ? 'completed' : resultForm.status
  selectedSample.value.comment = resultForm.note || selectedSample.value.comment
  selectedSample.value.updatedAt = new Date().toISOString()
  selectedSample.value.history.push({ id: Date.now(), status: selectedSample.value.status, date: new Date().toISOString(), actor: "Специалист лаборатории", note: 'Результаты обновлены.' })
  resultModalOpen.value = false
  toast.add({ title: 'Результат сохранён', color: 'success' })
}
function assignTest() { assignModalOpen.value = false; toast.add({ title: 'Испытание назначено', color: 'success' }) }

const canCloseSample = computed(() => selectedSample.value?.status === 'review')

const columnMenuItems = computed(() => [
  'code', 'patient.name', 'material', 'direction', 'status', 'priority', 'updatedAt', 'actions'
].map(k => {
  const labels: Record<string, string> = { code: 'Код', 'patient.name': 'Пациент', material: 'Материал', direction: 'Направление', status: 'Статус', priority: 'Приоритет', updatedAt: 'Обновлено', actions: 'Действия' }
  return {
    label: labels[k] ?? k,
    type: 'checkbox' as const,
    checked: columnVisibility.value[k] !== false,
    onUpdateChecked(v: boolean) { columnVisibility.value = { ...columnVisibility.value, [k]: v } },
    onSelect(e?: Event) { e?.preventDefault() },
  }
}))

const getRowActionItems = (sample: ResearchSample): DropdownMenuItem[] => [
  { label: 'Просмотр', icon: 'i-lucide-eye', onSelect: () => openDetail(sample) },
]

const handleRowSelect = (_event: Event, row: { original: ResearchSample }) => {
  if (isSkeletonRow(row.original)) {
    return
  }

  openDetail(row.original)
}

const contextMenuItems = computed(() =>
  contextRow.value ? getRowActionItems(contextRow.value) : [],
)

const handleRowContextmenu = async (event: Event, row: { original: ResearchSample }) => {
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

const resultStatusItems = [
  { label: 'В процессе', value: 'inProgress' }, { label: 'На проверке', value: 'review' },
  { label: 'Завершено', value: 'completed' }, { label: 'Отклонено', value: 'rejected' }
]
const interpretationItems = [
  { label: 'В процессе', value: 'pending' }, { label: 'Соответствует', value: 'normal' },
  { label: 'Отклонение', value: 'warning' }, { label: 'Критично', value: 'critical' }
]

</script>

<template>
  <UDashboardPanel id="research" :ui="{ body: 'min-h-0 overflow-hidden' }">
    <template #header>
      <UDashboardNavbar>
        <template #leading><UDashboardSidebarCollapse /></template>
        <template #title>
          <div class="flex min-w-0 items-center gap-2">
            <UIcon name="i-lucide-flask-conical" class="size-5 shrink-0 text-muted" />
            <span class="truncate font-semibold text-highlighted">{{ t('research.title') }}</span>
            <UBadge :label="filteredSamples.length" color="success" variant="subtle" class="shrink-0" />
          </div>
        </template>
      </UDashboardNavbar>

      <UDashboardToolbar>
        <template #left>
          <div class="flex w-full flex-col gap-3 lg:flex-row lg:items-center">
            <CrudSearchControl v-model="searchQuery" placeholder="Поиск по исследованиям" />
            <CrudFilterControls @clear="clearFilters" />
          </div>
        </template>
        <template #right>
          <div class="flex flex-wrap items-center gap-2">
            <UButton color="neutral" variant="subtle" icon="i-lucide-refresh-cw" label="Обновить" @click="table.refresh()" />
            <UDropdownMenu :items="columnMenuItems" :content="{ align: 'end' }">
              <UButton label="Столбцы" color="neutral" variant="subtle" trailing-icon="i-lucide-settings-2" />
            </UDropdownMenu>
          </div>
        </template>
      </UDashboardToolbar>
    </template>

    <template #body>
      <CrudDataTable
        v-model:column-visibility="columnVisibility"
        :data="tableRows"
        :columns="uiColumns"
        :total="table.total.value"
        :loading="table.loading.value"
        :loading-more="table.loadingMore.value"
        :has-more="table.hasMore.value"
        :table-ui="{ ...borderedCrudTableUi, tbody: 'cursor-pointer' }"
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
            :title="t('research.empty')"
            description="Измените фильтры или обновите очередь исследований."
          />
        </template>
      </CrudDataTable>
    </template>
  </UDashboardPanel>

  <ResearchDetailModal v-model:open="detailOpen" :sample="selectedSample"
    :readonly="false" :can-close-sample="canCloseSample" :can-assign-tests="true"
    @action="handleResearchAction" />

  <!-- Modals unchanged -->
  <UModal v-model:open="resultModalOpen" title="Результаты исследований образца" description="Заполните результаты образца по типовым показателям." :ui="{ content: 'max-w-6xl' }">
    <template #body>
      <div v-if="selectedSample" class="flex flex-col gap-4">
        <section class="grid gap-3 lg:grid-cols-[12rem_minmax(0,1fr)_12rem]">
          <UFormField label="Статус"><USelect v-model="resultForm.status" :items="resultStatusItems" value-key="value" class="w-full" /></UFormField>
          <UFormField label="Примечание"><UInput v-model="resultForm.note" /></UFormField>
          <UFormField label="Время выпуска"><UInput v-model="resultForm.issuedAt" type="datetime-local" /></UFormField>
          <UFormField label="Рекомендации" class="lg:col-span-2"><UInput v-model="resultForm.recommendations" /></UFormField>
          <div class="flex items-end"><UCheckbox v-model="resultForm.completed" label="Завершено" /></div>
        </section>
        <section>
          <div class="mb-2 flex items-center justify-between gap-3">
            <h3 class="text-sm font-semibold text-highlighted">Типовые показатели</h3>
            <UBadge :label="`${selectedSample.tests.length} показателей`" color="neutral" variant="subtle" />
          </div>
          <div class="overflow-x-auto rounded-lg border border-default">
            <table class="min-w-[960px] w-full border-collapse text-sm">
              <thead class="bg-elevated text-left text-xs font-medium uppercase text-muted">
                <tr><th class="border-b border-default px-3 py-2">Показатель</th><th class="border-b border-default px-3 py-2">Применяется</th><th class="border-b border-default px-3 py-2">Статус</th><th class="border-b border-default px-3 py-2">Результат</th><th class="border-b border-default px-3 py-2">Норма</th><th class="border-b border-default px-3 py-2">Ед.</th><th class="border-b border-default px-3 py-2">Примечание</th></tr>
              </thead>
              <tbody>
                <tr v-for="test in selectedSample.tests" :key="test.id" class="border-b border-default last:border-b-0 odd:bg-elevated/35">
                  <td class="px-3 py-2 align-top"><p class="font-medium text-highlighted">{{ test.name }}</p><p class="text-xs text-muted">{{ test.code }} · {{ test.group }}</p></td>
                  <td class="px-3 py-2 align-middle"><UCheckbox v-model="test.applies" /></td>
                  <td class="px-3 py-2 align-middle"><USelect v-model="test.interpretation" :items="interpretationItems" value-key="value" class="w-36" /></td>
                  <td class="px-3 py-2 align-middle"><UInput v-model="test.result" class="w-36" /></td>
                  <td class="px-3 py-2 align-middle"><UInput v-model="test.reference" class="w-36" /></td>
                  <td class="px-3 py-2 align-middle"><UInput v-model="test.unit" class="w-24" /></td>
                  <td class="px-3 py-2 align-middle"><UInput v-model="test.note" class="w-48" /></td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </template>
    <template #footer><UButton label="Отмена" color="neutral" variant="ghost" @click="resultModalOpen = false" /><UButton label="Сохранить" icon="i-lucide-save" @click="completeTest" /></template>
  </UModal>

  <UModal v-model:open="assignModalOpen" title="Назначить испытание" description="Доступно начальнику лаборатории.">
    <template #body><div class="grid gap-3 sm:grid-cols-2"><UInput v-model="assignForm.indicator" placeholder="Показатель" /><UInput v-model="assignForm.lab" placeholder="Лаборатория" /></div></template>
    <template #footer><UButton label="Отмена" color="neutral" variant="ghost" @click="assignModalOpen = false" /><UButton label="Назначить" icon="i-lucide-list-plus" @click="assignTest" /></template>
  </UModal>

  <UModal v-model:open="closeModalOpen" title="Закрытие образца" description="Укажите verdict для analyzed/review образца.">
    <template #body><UTextarea v-model="closeForm.verdict" autoresize class="w-full" placeholder="Введите заключение..." /></template>
    <template #footer><UButton label="Отмена" color="neutral" variant="ghost" @click="closeModalOpen = false" /><UButton label="Закрыть образец" icon="i-lucide-badge-check" @click="closeSample" /></template>
  </UModal>
</template>
