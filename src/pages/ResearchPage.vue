<script setup lang="ts">
import { breakpointsTailwind, useBreakpoints } from '@vueuse/core'
import type { DropdownMenuItem } from '@nuxt/ui'
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import ResearchDetail from '@/modules/research/components/ResearchDetail.vue'
import ResearchList from '@/modules/research/components/ResearchList.vue'
import { useResearchSamples } from '@/modules/research/composables/useResearchSamples'
import { useWorkflowRole } from '@/modules/workflows/useWorkflowRole'
import type { ResearchSample, ResearchStatus } from '@/shared/types'

type SortKey = 'updatedAt' | 'registeredAt' | 'code'
type PriorityFilter = 'all' | 'urgent' | 'normal'
type QuickFilter = 'all' | 'active' | 'completed' | 'urgent'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { samples, isFetching } = useResearchSamples()
const toast = useToast()
const { selectedMode, selectedRole, selectedRoleKey } = useWorkflowRole()

const query = ref('')
const selectedQuickFilter = ref<QuickFilter>('all')
const sortKey = ref<SortKey>('updatedAt')
const priorityFilter = ref<PriorityFilter>('all')
const visibleCount = ref(20)
const isLoadingMore = ref(false)
const closeModalOpen = ref(false)
const resultModalOpen = ref(false)
const assignModalOpen = ref(false)

const resultStatusItems = [
  { label: 'В процессе', value: 'inProgress' },
  { label: 'На проверке', value: 'review' },
  { label: 'Завершено', value: 'completed' },
  { label: 'Отклонено', value: 'rejected' }
]

const interpretationItems = [
  { label: 'В процессе', value: 'pending' },
  { label: 'Соответствует', value: 'normal' },
  { label: 'Отклонение', value: 'warning' },
  { label: 'Критично', value: 'critical' }
]

const resultForm = reactive({
  status: 'inProgress' as ResearchStatus,
  completed: false,
  note: '',
  recommendations: '',
  issuedAt: ''
})

const activeStatuses: ResearchStatus[] = ['registered', 'inProgress', 'review']
const quickFilters: QuickFilter[] = ['all', 'active', 'completed', 'urgent']

const quickFilterItems = computed(() => quickFilters.map(filter => ({
  label: t(`research.filters.${filter}`),
  value: filter,
  color: filter === 'urgent' ? 'error' as const : filter === 'active' ? 'success' as const : 'neutral' as const
})))

const filterItems = computed<DropdownMenuItem[][]>(() => [
  [
    { type: 'label', label: t('research.sortBy') },
    ...(['updatedAt', 'registeredAt', 'code'] as SortKey[]).map(key => ({
      label: t(`research.sort.${key}`),
      icon: sortKey.value === key ? 'i-lucide-check' : 'i-lucide-arrow-up-down',
      onSelect: () => {
        sortKey.value = key
      }
    }))
  ],
  [
    { type: 'label', label: t('research.priority.label') },
    ...(['all', 'urgent', 'normal'] as PriorityFilter[]).map(priority => ({
      label: t(`research.priority.${priority}`),
      type: 'checkbox' as const,
      checked: priorityFilter.value === priority,
      onUpdateChecked: () => {
        priorityFilter.value = priority
      },
      onSelect: (event?: Event) => {
        event?.preventDefault()
      }
    }))
  ]
])

const filteredSamples = computed<ResearchSample[]>(() => {
  const normalizedQuery = query.value.trim().toLocaleLowerCase()
  const filtered: ResearchSample[] = []

  for (const sample of samples.value as ResearchSample[]) {
    const matchesQuickFilter = selectedQuickFilter.value === 'all'
      || (selectedQuickFilter.value === 'active' && activeStatuses.includes(sample.status))
      || (selectedQuickFilter.value === 'completed' && sample.status === 'completed')
      || (selectedQuickFilter.value === 'urgent' && sample.priority === 'urgent')
    const matchesPriority = priorityFilter.value === 'all' || sample.priority === priorityFilter.value
    const matchesQuery = !normalizedQuery
      || sample.code.toLocaleLowerCase().includes(normalizedQuery)
      || sample.patient.name.toLocaleLowerCase().includes(normalizedQuery)
      || sample.material.toLocaleLowerCase().includes(normalizedQuery)
      || sample.direction.toLocaleLowerCase().includes(normalizedQuery)

    if (matchesQuickFilter && matchesPriority && matchesQuery) {
      filtered.push(sample)
    }
  }

  return [...filtered].sort((first, second) => {
    if (sortKey.value === 'code') {
      return first.code.localeCompare(second.code)
    }

    const firstDate = sortKey.value === 'registeredAt' ? first.registeredAt : first.updatedAt
    const secondDate = sortKey.value === 'registeredAt' ? second.registeredAt : second.updatedAt

    return new Date(secondDate).getTime() - new Date(firstDate).getTime()
  })
})

const visibleSamples = computed(() => filteredSamples.value.slice(0, visibleCount.value))
const hasMore = computed(() => visibleSamples.value.length < filteredSamples.value.length)
const selectedSample = ref<ResearchSample | null>(null)

const isSamplePanelOpen = computed({
  get() {
    return !!selectedSample.value
  },
  set(value: boolean) {
    if (!value) {
      selectedSample.value = null
    }
  }
})

const readonlyMode = computed(() => selectedMode.value === 'readonly')
const canCloseSample = computed(() => selectedRoleKey.value === 'lab_chief' && selectedSample.value?.status === 'review')
const canAssignTests = computed(() => selectedRoleKey.value === 'lab_chief')

const activeFilterCount = computed(() => {
  let count = 0
  if (query.value.trim()) count += 1
  if (selectedQuickFilter.value !== 'all') count += 1
  if (priorityFilter.value !== 'all') count += 1
  return count
})

function setSelectedSample(sample: ResearchSample | null | undefined) {
  selectedSample.value = sample ?? null

  if (sample) {
    if (route.query.id !== String(sample.id)) {
      router.replace({ query: { ...route.query, id: String(sample.id) } })
    }
    return
  }

  if (route.query.id) {
    const nextQuery = { ...route.query }
    delete nextQuery.id
    router.replace({ query: nextQuery })
  }
}

function clearFilters() {
  query.value = ''
  selectedQuickFilter.value = 'all'
  priorityFilter.value = 'all'
}

function loadMore() {
  if (!hasMore.value || isLoadingMore.value) {
    return
  }

  isLoadingMore.value = true
  window.setTimeout(() => {
    visibleCount.value += 20
    isLoadingMore.value = false
  }, 250)
}

function handleResearchAction(action: string) {
  if (action === 'close-sample') {
    closeModalOpen.value = true
    return
  }

  if (action === 'assign-test') {
    assignModalOpen.value = true
    return
  }

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
  if (selectedSample.value) {
    selectedSample.value.status = 'completed'
    selectedSample.value.history.push({
      id: Date.now(),
      status: 'completed',
      date: new Date().toISOString(),
      actor: selectedRole.value.title,
      note: 'Образец закрыт с verdict после проверки истории.'
    })
  }
  closeModalOpen.value = false
  toast.add({ title: 'Образец закрыт', color: 'success' })
}

function completeTest() {
  if (selectedSample.value) {
    selectedSample.value.status = resultForm.completed ? 'completed' : resultForm.status
    selectedSample.value.comment = resultForm.note || selectedSample.value.comment
    selectedSample.value.updatedAt = new Date().toISOString()
    selectedSample.value.history.push({
      id: Date.now(),
      status: selectedSample.value.status,
      date: new Date().toISOString(),
      actor: selectedRole.value.title,
      note: resultForm.completed
        ? 'Результаты типовых показателей внесены, образец завершён.'
        : 'Результаты типовых показателей обновлены.'
    })
  }
  resultModalOpen.value = false
  toast.add({ title: 'Результат сохранён', color: 'success' })
}

function assignTest() {
  assignModalOpen.value = false
  toast.add({ title: 'Испытание назначено', color: 'success' })
}

watch([query, selectedQuickFilter, priorityFilter, sortKey], () => {
  visibleCount.value = 20
})

watch(filteredSamples, () => {
  if (!filteredSamples.value.find(sample => sample.id === selectedSample.value?.id)) {
    selectedSample.value = null
  }
})

watch([samples, () => route.query.id], () => {
  const rawId = route.query.id
  const id = typeof rawId === 'string' ? Number(rawId) : Number.NaN

  if (!Number.isFinite(id)) {
    return
  }

  const sample = samples.value.find(item => item.id === id) ?? null
  if (!sample) {
    setSelectedSample(null)
    return
  }

  if (selectedSample.value?.id !== sample.id) {
    setSelectedSample(sample)
  }
}, { immediate: true })

const breakpoints = useBreakpoints(breakpointsTailwind)
const isMobile = breakpoints.smaller('lg')
</script>

<template>
  <UDashboardPanel
    id="research-1"
    :default-size="28"
    :min-size="22"
    :max-size="34"
    resizable
  >
    <UDashboardNavbar>
      <template #leading>
        <UDashboardSidebarCollapse />
      </template>

      <template #title>
        <div class="flex min-w-0 items-center gap-2">
          <UIcon name="i-lucide-flask-conical" class="size-5 shrink-0 text-muted" />
          <span class="truncate font-semibold text-highlighted">
            {{ t('research.title') }}
          </span>
          <UBadge
            :label="filteredSamples.length"
            color="success"
            variant="subtle"
            class="shrink-0"
          />
          <UBadge
            :label="selectedRole.shortName"
            color="primary"
            variant="subtle"
            class="shrink-0"
          />
        </div>
      </template>
    </UDashboardNavbar>

    <UDashboardToolbar>
      <div class="flex w-full flex-col gap-3">
        <UFieldGroup class="w-full">
          <UBadge
            color="neutral"
            variant="outline"
            size="lg"
            icon="i-lucide-search"
            class="px-2"
          />
          <UInput
            v-model="query"
            :placeholder="t('research.search')"
            class="min-w-0 flex-1"
          >
            <template v-if="query" #trailing>
              <UButton
                color="neutral"
                variant="link"
                size="sm"
                icon="i-lucide-x"
                @click="query = ''"
              />
            </template>
          </UInput>

          <UDropdownMenu
            :items="filterItems"
            :content="{ align: 'end', side: 'bottom', sideOffset: 5 }"
          >
            <UButton
              color="neutral"
              variant="outline"
              icon="i-lucide-filter"
              :aria-label="t('common.filter')"
            >
              <template v-if="activeFilterCount" #trailing>
                <UKbd>{{ activeFilterCount }}</UKbd>
              </template>
            </UButton>
          </UDropdownMenu>

          <UTooltip :text="t('common.clearFilters')">
            <UButton
              color="neutral"
              variant="subtle"
              size="sm"
              class="px-2"
              icon="i-lucide-filter-x"
              @click="clearFilters"
            />
          </UTooltip>
        </UFieldGroup>

        <div class="flex w-full items-center gap-1 overflow-x-auto rounded-lg bg-elevated p-1">
          <UButton
            v-for="item in quickFilterItems"
            :key="item.value"
            size="xs"
            :color="item.color"
            :variant="selectedQuickFilter === item.value ? 'solid' : 'ghost'"
            class="shrink-0"
            :label="item.label"
            @click="selectedQuickFilter = item.value"
          />
        </div>

        <div class="flex flex-wrap items-center gap-2 text-xs text-muted">
          <UBadge :label="readonlyMode ? 'Только просмотр' : 'Операционная очередь'" color="neutral" variant="outline" />
          <UBadge
            v-if="canAssignTests"
            label="Закрытие образцов и справочники"
            color="primary"
            variant="subtle"
          />
        </div>
      </div>
    </UDashboardToolbar>

    <ResearchList
      v-model="selectedSample"
      :samples="visibleSamples"
      :loading="isFetching || isLoadingMore"
      :has-more="hasMore"
      @update:model-value="setSelectedSample"
      @load-more="loadMore"
    />
  </UDashboardPanel>

  <ResearchDetail
    v-if="selectedSample"
    :sample="selectedSample"
    :readonly="readonlyMode"
    :can-close-sample="canCloseSample"
    :can-assign-tests="canAssignTests"
    @close="setSelectedSample(null)"
    @action="handleResearchAction"
  />
  <div v-else class="hidden flex-1 flex-col items-center justify-center gap-3 lg:flex">
    <UIcon name="i-lucide-flask-conical" class="size-32 text-dimmed" />
    <p class="text-sm text-muted">
      {{ filteredSamples.length ? t('research.open') : t('research.empty') }}
    </p>
  </div>

  <USlideover v-if="isMobile" v-model:open="isSamplePanelOpen">
    <template #content>
      <ResearchDetail
        v-if="selectedSample"
        :sample="selectedSample"
        :readonly="readonlyMode"
        :can-close-sample="canCloseSample"
        :can-assign-tests="canAssignTests"
        @close="setSelectedSample(null)"
        @action="handleResearchAction"
      />
    </template>
  </USlideover>

  <UModal
    v-model:open="resultModalOpen"
    title="Результаты исследований образца"
    description="Заполните результаты образца по типовым показателям."
    :ui="{ content: 'max-w-6xl' }"
  >
    <template #body>
      <div v-if="selectedSample" class="flex flex-col gap-4">
        <section class="grid gap-3 lg:grid-cols-[12rem_minmax(0,1fr)_12rem]">
          <UFormField label="Статус">
            <USelect
              v-model="resultForm.status"
              :items="resultStatusItems"
              value-key="value"
              class="w-full"
            />
          </UFormField>

          <UFormField label="Примечание">
            <UInput v-model="resultForm.note" />
          </UFormField>

          <UFormField label="Время выпуска">
            <UInput v-model="resultForm.issuedAt" type="datetime-local" />
          </UFormField>

          <UFormField label="Рекомендации" class="lg:col-span-2">
            <UInput v-model="resultForm.recommendations" />
          </UFormField>

          <div class="flex items-end">
            <UCheckbox v-model="resultForm.completed" label="Завершено" />
          </div>
        </section>

        <section>
          <div class="mb-2 flex items-center justify-between gap-3">
            <h3 class="text-sm font-semibold text-highlighted">
              Типовые показатели
            </h3>
            <UBadge
              :label="`${selectedSample.tests.length} показателей`"
              color="neutral"
              variant="subtle"
            />
          </div>

          <div class="overflow-x-auto rounded-lg border border-default">
            <table class="min-w-[960px] w-full border-collapse text-sm">
              <thead class="bg-elevated text-left text-xs font-medium uppercase text-muted">
                <tr>
                  <th class="border-b border-default px-3 py-2">
                    Показатель
                  </th>
                  <th class="border-b border-default px-3 py-2">
                    Применяется
                  </th>
                  <th class="border-b border-default px-3 py-2">
                    Статус
                  </th>
                  <th class="border-b border-default px-3 py-2">
                    Результат
                  </th>
                  <th class="border-b border-default px-3 py-2">
                    Норма
                  </th>
                  <th class="border-b border-default px-3 py-2">
                    Ед.
                  </th>
                  <th class="border-b border-default px-3 py-2">
                    Примечание
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="test in selectedSample.tests"
                  :key="test.id"
                  class="border-b border-default last:border-b-0 odd:bg-elevated/35"
                >
                  <td class="px-3 py-2 align-top">
                    <p class="font-medium text-highlighted">
                      {{ test.name }}
                    </p>
                    <p class="text-xs text-muted">
                      {{ test.code }} · {{ test.group }}
                    </p>
                  </td>
                  <td class="px-3 py-2 align-middle">
                    <UCheckbox v-model="test.applies" />
                  </td>
                  <td class="px-3 py-2 align-middle">
                    <USelect
                      v-model="test.interpretation"
                      :items="interpretationItems"
                      value-key="value"
                      class="w-36"
                    />
                  </td>
                  <td class="px-3 py-2 align-middle">
                    <UInput v-model="test.result" class="w-36" />
                  </td>
                  <td class="px-3 py-2 align-middle">
                    <UInput v-model="test.reference" class="w-36" />
                  </td>
                  <td class="px-3 py-2 align-middle">
                    <UInput v-model="test.unit" class="w-24" />
                  </td>
                  <td class="px-3 py-2 align-middle">
                    <UInput v-model="test.note" class="w-48" />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </template>
    <template #footer>
      <UButton
        label="Отмена"
        color="neutral"
        variant="ghost"
        @click="resultModalOpen = false"
      />
      <UButton label="Сохранить" icon="i-lucide-save" @click="completeTest" />
    </template>
  </UModal>

  <UModal v-model:open="assignModalOpen" title="Назначить испытание" description="Доступно начальнику лаборатории.">
    <template #body>
      <div class="grid gap-3 sm:grid-cols-2">
        <UInput model-value="Новый показатель" placeholder="Показатель" />
        <UInput model-value="Микробиология" placeholder="Лаборатория" />
      </div>
    </template>
    <template #footer>
      <UButton
        label="Отмена"
        color="neutral"
        variant="ghost"
        @click="assignModalOpen = false"
      />
      <UButton label="Назначить" icon="i-lucide-list-plus" @click="assignTest" />
    </template>
  </UModal>

  <UModal v-model:open="closeModalOpen" title="Закрытие образца" description="Укажите verdict для analyzed/review образца.">
    <template #body>
      <UTextarea model-value="Verdict: соответствует требованиям." autoresize class="w-full" />
    </template>
    <template #footer>
      <UButton
        label="Отмена"
        color="neutral"
        variant="ghost"
        @click="closeModalOpen = false"
      />
      <UButton label="Закрыть образец" icon="i-lucide-badge-check" @click="closeSample" />
    </template>
  </UModal>
</template>
