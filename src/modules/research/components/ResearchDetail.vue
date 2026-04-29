<script setup lang="ts">
import { format } from 'date-fns'
import { computed, h, ref, resolveComponent } from 'vue'
import type { StepperItem, TableColumn, TabsItem } from '@nuxt/ui'
import { useI18n } from 'vue-i18n'
import { useLocale } from '@/shared/composables/useLocale'
import type { ResearchSample, ResearchStatus, ResearchTest } from '@/shared/types'

interface RelatedSample {
  id: number
  code: string
  material: string
  direction: string
  status: ResearchStatus
  updatedAt: string
}

const props = defineProps<{
  sample: ResearchSample
  readonly?: boolean
  canCloseSample?: boolean
  canAssignTests?: boolean
}>()

const emit = defineEmits<{
  close: []
  action: [action: string]
}>()

const { t } = useI18n()
const { dateFnsLocale } = useLocale()
const UBadge = resolveComponent('UBadge')
const selectedTab = ref<'summary' | 'related'>('summary')

const statusColors: Record<ResearchStatus, 'neutral' | 'primary' | 'info' | 'success' | 'error'> = {
  registered: 'neutral',
  inProgress: 'primary',
  review: 'info',
  completed: 'success',
  rejected: 'error'
}

const statusIcons: Record<ResearchStatus, string> = {
  registered: 'i-lucide-clipboard-check',
  inProgress: 'i-lucide-flask-conical',
  review: 'i-lucide-search-check',
  completed: 'i-lucide-circle-check',
  rejected: 'i-lucide-circle-x'
}

const interpretationColors: Record<ResearchTest['interpretation'], 'neutral' | 'success' | 'warning' | 'error'> = {
  normal: 'success',
  warning: 'warning',
  critical: 'error',
  pending: 'neutral'
}

const interpretationLabels: Record<ResearchTest['interpretation'], string> = {
  normal: 'Норма',
  warning: 'Отклонение',
  critical: 'Критично',
  pending: 'Ожидается'
}

const currentStatusColor = computed(() => statusColors[props.sample.status])
const appliedTests = computed(() => props.sample.tests.filter(test => test.applies))
const resultSummary = computed(() => ({
  total: props.sample.tests.length,
  applied: appliedTests.value.length,
  deviations: props.sample.tests.filter(test => test.applies && ['warning', 'critical'].includes(test.interpretation)).length,
  pending: props.sample.tests.filter(test => test.applies && test.interpretation === 'pending').length
}))
const tabItems = computed<TabsItem[]>(() => [
  {
    label: 'Результаты',
    icon: 'i-lucide-flask-conical',
    value: 'summary',
    slot: 'summary' as const
  },
  {
    label: 'Связанные образцы',
    icon: 'i-lucide-git-branch',
    value: 'related',
    slot: 'related' as const
  }
])

const historyStepperItems = computed<StepperItem[]>(() => props.sample.history.map(entry => ({
  title: t(`research.status.${entry.status}`),
  description: `${formatDate(entry.date)} · ${entry.actor}\n${entry.note}`,
  icon: statusIcons[entry.status],
  value: entry.id
})))

const relatedSamples = computed<RelatedSample[]>(() => {
  const statuses: ResearchStatus[] = ['registered', 'inProgress', 'review', 'completed']

  return Array.from({ length: 4 }, (_, index) => ({
    id: props.sample.id * 10 + index,
    code: `${props.sample.code}-R${index + 1}`,
    material: index % 2 === 0 ? props.sample.material : 'Сыворотка',
    direction: index % 2 === 0 ? props.sample.direction : 'Биохимия',
    status: statuses[(props.sample.id + index) % statuses.length],
    updatedAt: new Date(new Date(props.sample.updatedAt).getTime() - (index + 1) * 86400000).toISOString()
  }))
})

const relatedColumns = computed<TableColumn<RelatedSample>[]>(() => [
  {
    accessorKey: 'code',
    header: t('research.fields.sample')
  },
  {
    accessorKey: 'material',
    header: t('research.fields.material')
  },
  {
    accessorKey: 'direction',
    header: t('research.fields.direction')
  },
  {
    accessorKey: 'status',
    header: t('research.fields.status'),
    cell: ({ row }) => h(UBadge, {
      color: statusColors[row.original.status],
      variant: 'subtle',
      label: t(`research.status.${row.original.status}`)
    })
  },
  {
    accessorKey: 'updatedAt',
    header: t('research.updatedAt'),
    cell: ({ row }) => formatDate(row.original.updatedAt)
  }
])

const resultColumns = computed<TableColumn<ResearchTest>[]>(() => [
  {
    accessorKey: 'applies',
    header: 'Прим.',
    cell: ({ row }) => h(UBadge, {
      color: row.original.applies ? 'primary' : 'neutral',
      variant: 'subtle',
      label: row.original.applies ? 'Да' : 'Нет'
    })
  },
  {
    accessorKey: 'code',
    header: 'Код',
    cell: ({ row }) => h('span', { class: 'font-mono text-xs text-muted' }, row.original.code)
  },
  {
    accessorKey: 'name',
    header: 'Типовой показатель',
    cell: ({ row }) => h('div', { class: 'min-w-0' }, [
      h('p', { class: 'truncate text-sm font-medium text-highlighted' }, row.original.name),
      h('p', { class: 'truncate text-xs text-muted' }, row.original.group)
    ])
  },
  {
    accessorKey: 'method',
    header: 'Метод'
  },
  {
    accessorKey: 'reference',
    header: 'Норма',
    cell: ({ row }) => `${row.original.reference} ${row.original.unit}`
  },
  {
    accessorKey: 'result',
    header: 'Результат',
    cell: ({ row }) => h(
      'span',
      {
        class: row.original.interpretation === 'normal'
          ? 'font-semibold text-toned'
          : 'font-semibold text-warning'
      },
      `${row.original.result} ${row.original.unit}`
    )
  },
  {
    accessorKey: 'interpretation',
    header: 'Оценка',
    cell: ({ row }) => h(UBadge, {
      color: interpretationColors[row.original.interpretation],
      variant: 'subtle',
      label: interpretationLabels[row.original.interpretation]
    })
  },
  {
    accessorKey: 'note',
    header: 'Примечание',
    cell: ({ row }) => row.original.note || '-'
  }
])

function formatDate(date: string) {
  return format(new Date(date), 'dd MMM yyyy, HH:mm', { locale: dateFnsLocale.value })
}
</script>

<template>
  <UDashboardPanel id="research-2">
    <UDashboardNavbar :title="sample.code" :toggle="false">
      <template #leading>
        <UButton
          icon="i-lucide-x"
          color="neutral"
          variant="ghost"
          class="-ms-1.5"
          @click="emit('close')"
        />
      </template>

      <template #right>
        <UBadge
          :color="currentStatusColor"
          variant="subtle"
          :label="t(`research.status.${sample.status}`)"
        />
      </template>
    </UDashboardNavbar>

    <div class="flex-1 overflow-y-auto">
      <div class="border-b border-default px-4 pt-5 sm:px-6">
        <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <UBadge
                :color="currentStatusColor"
                variant="solid"
                size="sm"
                class="uppercase"
                :label="t(`research.status.${sample.status}`)"
              />
              <span class="text-xs font-medium text-muted">
                {{ t('research.fields.sampleId') }}: {{ sample.code }}
              </span>
            </div>

            <h2 class="mt-2 truncate text-2xl font-semibold text-highlighted">
              {{ sample.patient.name }}
            </h2>

            <p class="mt-1 truncate text-sm text-muted">
              {{ sample.material }} / {{ sample.direction }} · {{ sample.patient.location }}
            </p>

            <div class="mt-3 flex flex-wrap items-center gap-2">
              <UBadge color="neutral" variant="outline" :label="sample.patient.email" />
              <UBadge
                :color="sample.priority === 'urgent' ? 'warning' : 'neutral'"
                variant="subtle"
                :label="t(`research.priority.${sample.priority}`)"
              />
              <UBadge color="neutral" variant="outline" :label="formatDate(sample.updatedAt)" />
            </div>
          </div>

          <div class="flex shrink-0 items-center gap-2">
            <UButton
              v-if="!readonly"
              color="neutral"
              variant="outline"
              size="sm"
              label="Вернуть в очередь"
              icon="i-lucide-rotate-ccw"
              @click="emit('action', 'return-test')"
            />
            <UButton
              v-if="!readonly"
              color="primary"
              size="sm"
              label="Внести результат"
              icon="i-lucide-pencil-line"
              @click="emit('action', 'complete-test')"
            />
            <UButton
              v-if="canAssignTests"
              color="neutral"
              variant="outline"
              size="sm"
              label="Назначить испытание"
              icon="i-lucide-list-plus"
              @click="emit('action', 'assign-test')"
            />
            <UButton
              v-if="canCloseSample"
              color="primary"
              size="sm"
              label="Закрыть образец"
              icon="i-lucide-badge-check"
              @click="emit('action', 'close-sample')"
            />
          </div>
        </div>

        <UTabs
          v-model="selectedTab"
          :items="tabItems"
          variant="link"
          :content="false"
          class="mt-5"
        />
      </div>

      <div class="p-4 sm:p-6">
        <div
          v-if="selectedTab === 'summary'"
          class="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(18rem,22rem)]"
        >
          <section>
            <div class="mb-4 overflow-hidden rounded-lg border border-default">
              <div class="border-b border-default bg-elevated px-4 py-3">
                <h3 class="text-base font-semibold text-highlighted">
                  Результат образца
                </h3>
              </div>

              <dl class="grid text-sm sm:grid-cols-2">
                <div class="grid grid-cols-[10rem_minmax(0,1fr)] border-b border-default sm:border-e">
                  <dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">
                    Образец №
                  </dt>
                  <dd class="px-3 py-2 text-muted">
                    {{ sample.code }}
                  </dd>
                </div>
                <div class="grid grid-cols-[10rem_minmax(0,1fr)] border-b border-default">
                  <dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">
                    Тип образца
                  </dt>
                  <dd class="px-3 py-2 text-muted">
                    {{ sample.material }}
                  </dd>
                </div>
                <div class="grid grid-cols-[10rem_minmax(0,1fr)] border-b border-default sm:border-e">
                  <dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">
                    Наименование
                  </dt>
                  <dd class="px-3 py-2 text-muted">
                    {{ sample.direction }} · {{ sample.patient.name }}
                  </dd>
                </div>
                <div class="grid grid-cols-[10rem_minmax(0,1fr)] border-b border-default">
                  <dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">
                    Подразделение
                  </dt>
                  <dd class="px-3 py-2 text-muted">
                    {{ sample.patient.location }}
                  </dd>
                </div>
                <div class="grid grid-cols-[10rem_minmax(0,1fr)] border-b border-default sm:border-e">
                  <dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">
                    Статус
                  </dt>
                  <dd class="px-3 py-2">
                    <UBadge
                      :color="currentStatusColor"
                      variant="subtle"
                      :label="t(`research.status.${sample.status}`)"
                    />
                  </dd>
                </div>
                <div class="grid grid-cols-[10rem_minmax(0,1fr)] border-b border-default">
                  <dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">
                    Завершено
                  </dt>
                  <dd class="px-3 py-2 text-muted">
                    {{ sample.status === 'completed' ? 'Да' : 'Нет' }}
                  </dd>
                </div>
                <div class="grid grid-cols-[10rem_minmax(0,1fr)] border-b border-default sm:border-b-0 sm:border-e">
                  <dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">
                    Время доставки
                  </dt>
                  <dd class="px-3 py-2 text-muted">
                    {{ formatDate(sample.registeredAt) }}
                  </dd>
                </div>
                <div class="grid grid-cols-[10rem_minmax(0,1fr)]">
                  <dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">
                    Время выпуска
                  </dt>
                  <dd class="px-3 py-2 text-muted">
                    {{ sample.status === 'completed' ? formatDate(sample.updatedAt) : 'Не выпущен' }}
                  </dd>
                </div>
              </dl>
            </div>

            <div class="mb-3 flex flex-col gap-3">
              <div class="flex items-center gap-2">
                <UIcon name="i-lucide-flask-conical" class="size-4 text-muted" />
                <h3 class="text-sm font-semibold text-highlighted">
                  Результаты исследований по типовым показателям
                </h3>
              </div>

              <div class="grid gap-2 sm:grid-cols-4">
                <div class="rounded-lg border border-default bg-elevated/40 p-3">
                  <p class="text-xs text-muted">
                    Всего
                  </p>
                  <p class="mt-1 text-xl font-semibold text-highlighted">
                    {{ resultSummary.total }}
                  </p>
                </div>
                <div class="rounded-lg border border-default bg-elevated/40 p-3">
                  <p class="text-xs text-muted">
                    Применяется
                  </p>
                  <p class="mt-1 text-xl font-semibold text-highlighted">
                    {{ resultSummary.applied }}
                  </p>
                </div>
                <div class="rounded-lg border border-default bg-elevated/40 p-3">
                  <p class="text-xs text-muted">
                    Отклонения
                  </p>
                  <p class="mt-1 text-xl font-semibold text-highlighted">
                    {{ resultSummary.deviations }}
                  </p>
                </div>
                <div class="rounded-lg border border-default bg-elevated/40 p-3">
                  <p class="text-xs text-muted">
                    Ожидается
                  </p>
                  <p class="mt-1 text-xl font-semibold text-highlighted">
                    {{ resultSummary.pending }}
                  </p>
                </div>
              </div>
            </div>

            <div class="overflow-hidden rounded-lg border border-default">
              <UTable
                :data="sample.tests"
                :columns="resultColumns"
                :ui="{
                  th: 'px-4 py-2 text-left text-sm font-semibold text-highlighted',
                  td: 'px-4 py-2 align-middle text-sm text-muted whitespace-nowrap'
                }"
              />
            </div>
          </section>

          <section>
            <div class="mb-3 flex items-center gap-2">
              <UIcon name="i-lucide-history" class="size-4 text-muted" />
              <h3 class="text-sm font-semibold text-highlighted">
                {{ t('research.historyTitle') }}
              </h3>
            </div>

            <UStepper
              orientation="vertical"
              :items="historyStepperItems"
              :default-value="historyStepperItems.length - 1"
              disabled
              class="w-full"
              :ui="{
                item: 'items-start',
                title: 'text-sm font-semibold text-highlighted',
                description: 'whitespace-pre-line text-xs leading-5 text-muted',
                separator: 'min-h-8'
              }"
            />
          </section>
        </div>

        <div v-else class="overflow-hidden rounded-lg border border-default">
          <UTable
            :data="relatedSamples"
            :columns="relatedColumns"
            :ui="{
              th: 'px-4 py-2 text-sm text-highlighted text-left font-semibold',
              td: 'px-4 py-2 text-sm text-muted whitespace-nowrap'
            }"
          />
        </div>
      </div>
    </div>
  </UDashboardPanel>
</template>
