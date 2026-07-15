<script setup lang="ts">
// Страница «Рабочие процессы» — реестр шаблонов журналов (рабочих процессов)
// в таблице + конструктор процесса в полноэкранной модалке (как в направлениях).
import { computed, onMounted, ref } from 'vue'
import type { TableColumn, TableRow } from '@nuxt/ui'
import JournalBuilder from '@/modules/journals/components/JournalBuilder.vue'
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
import type { JournalSchema, JournalTemplate } from '@/modules/journals/types/journal'

const toast = useToast()

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

function refresh() {
  templates.value = getTemplates()
}

onMounted(() => {
  initDemoData([patientIntake, microbiologyStudy])
  refresh()
})

const rows = computed<WorkflowRow[]>(() => {
  const query = search.value.trim().toLowerCase()
  return templates.value
    .filter((template) => !query || template.title.toLowerCase().includes(query))
    .map((template) => ({
      id: template.id,
      title: template.title,
      versions: template.versions.length,
      currentVersion: template.currentVersion,
      entries: template.versions.reduce((sum, version) => sum + version.entries.length, 0),
      updatedAt: template.updatedAt,
    }))
})

const columns: TableColumn<WorkflowRow>[] = [
  { accessorKey: 'title', header: 'Название' },
  { accessorKey: 'versions', header: 'Версий' },
  { accessorKey: 'currentVersion', header: 'Текущая' },
  { accessorKey: 'entries', header: 'Записей' },
  { accessorKey: 'updatedAt', header: 'Обновлён' },
  { id: 'actions' },
]

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('ru-RU')
}

// ─── Конструктор (полноэкранная модалка) ──────────────────────────────────
const builderOpen = ref(false)
const selectedId = ref<string | null>(null)
const builderSchema = ref<JournalSchema | null>(null)

const selectedTemplate = computed(() =>
  selectedId.value ? getTemplate(selectedId.value) ?? null : null,
)

const builderTitle = computed(() =>
  selectedTemplate.value ? `Конструктор процесса — ${selectedTemplate.value.title}` : 'Конструктор процесса',
)
const builderDescription = computed(() => {
  const template = selectedTemplate.value
  if (!template) {
    return undefined
  }
  return `Версия ${template.currentVersion} из ${template.versions.length}`
})

function openBuilder(id: string) {
  const template = getTemplate(id)
  if (!template) {
    return
  }
  selectedId.value = id
  builderSchema.value = template.versions[template.currentVersion - 1]?.schema ?? null
  builderOpen.value = true
}

function onVersionSaved(version: number) {
  refresh()
  toast.add({ title: `Сохранена версия ${version}`, color: 'success', icon: 'i-lucide-check' })
}

function onBuilderClose(open: boolean) {
  builderOpen.value = open
  if (!open) {
    selectedId.value = null
    builderSchema.value = null
    refresh()
  }
}

// ─── Создание нового процесса ─────────────────────────────────────────────
const newModalOpen = ref(false)
const newTitle = ref('')

function createWorkflow() {
  const title = newTitle.value.trim()
  if (!title) {
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
  newModalOpen.value = false
  newTitle.value = ''
  refresh()
  openBuilder(template.id)
}

// ─── Действия строки ──────────────────────────────────────────────────────
function rowActions(row: WorkflowRow) {
  return [
    [
      {
        label: 'Открыть конструктор',
        icon: 'i-lucide-workflow',
        onSelect: () => openBuilder(row.id),
      },
      {
        label: 'Переименовать',
        icon: 'i-lucide-pencil',
        onSelect: () => {
          const next = window.prompt('Новое название процесса:', row.title)
          if (next && next.trim()) {
            renameTemplate(row.id, next.trim())
            refresh()
          }
        },
      },
    ],
    [
      {
        label: 'Удалить',
        icon: 'i-lucide-trash-2',
        color: 'error' as const,
        onSelect: () => {
          if (window.confirm('Удалить процесс и все связанные записи?')) {
            deleteTemplate(row.id)
            refresh()
          }
        },
      },
    ],
  ]
}
</script>

<template>
  <UDashboardPanel id="workflows" :ui="{ body: 'min-h-0 overflow-hidden' }">
    <template #header>
      <UDashboardNavbar title="Рабочие процессы">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <UButton
            label="Новый процесс"
            icon="i-lucide-plus"
            @click="newModalOpen = true"
          />
        </template>
      </UDashboardNavbar>

      <UDashboardToolbar>
        <template #left>
          <UInput
            v-model="search"
            icon="i-lucide-search"
            placeholder="Поиск по процессам"
            class="w-full lg:w-80"
          />
        </template>
        <template #right>
          <UButton
            label="Обновить"
            color="neutral"
            variant="subtle"
            icon="i-lucide-refresh-cw"
            @click="refresh"
          />
        </template>
      </UDashboardToolbar>
    </template>

    <template #body>
      <div class="flex h-full min-h-0 w-full flex-col">
        <UTable
          :data="rows"
          :columns="columns"
          class="flex-1"
          :ui="{ tr: 'cursor-pointer' }"
          @select="(_e: Event, row: TableRow<WorkflowRow>) => openBuilder(row.original.id)"
        >
          <template #title-cell="{ row }">
            <div class="flex items-center gap-2 font-medium">
              <UIcon name="i-lucide-file-text" class="size-4 text-muted" />
              {{ row.original.title }}
            </div>
          </template>
          <template #currentVersion-cell="{ row }">
            <UBadge color="neutral" variant="subtle" size="sm">
              v{{ row.original.currentVersion }}
            </UBadge>
          </template>
          <template #updatedAt-cell="{ row }">
            <span class="text-muted">{{ formatDate(row.original.updatedAt) }}</span>
          </template>
          <template #actions-cell="{ row }">
            <div class="text-right">
              <UDropdownMenu :items="rowActions(row.original)" :content="{ align: 'end' }">
                <UButton
                  icon="i-lucide-ellipsis-vertical"
                  color="neutral"
                  variant="ghost"
                  @click.stop
                />
              </UDropdownMenu>
            </div>
          </template>
          <template #empty>
            <div class="py-12 text-center text-muted">
              <UIcon name="i-lucide-workflow" class="mx-auto mb-3 size-10 opacity-50" />
              <p>Пока нет ни одного рабочего процесса.</p>
            </div>
          </template>
        </UTable>
      </div>
    </template>
  </UDashboardPanel>

  <!-- Конструктор процесса во весь экран -->
  <UModal
    :open="builderOpen"
    fullscreen
    :title="builderTitle"
    :description="builderDescription"
    :ui="{ body: 'p-0 sm:p-0' }"
    @update:open="onBuilderClose"
  >
    <template #body>
      <div class="h-full p-4">
        <JournalBuilder
          v-if="builderSchema && selectedId"
          :key="selectedId"
          v-model="builderSchema"
          :template-id="selectedId"
          @version-saved="onVersionSaved"
        />
      </div>
    </template>
  </UModal>

  <!-- Новый процесс -->
  <UModal v-model:open="newModalOpen" title="Новый рабочий процесс">
    <template #body>
      <UFormField label="Название" required>
        <UInput
          v-model="newTitle"
          placeholder="например: Микробиологическое исследование"
          autofocus
          @keyup.enter="createWorkflow"
        />
      </UFormField>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton
          color="neutral"
          variant="ghost"
          label="Отмена"
          @click="newModalOpen = false"
        />
        <UButton label="Создать" :disabled="!newTitle.trim()" @click="createWorkflow" />
      </div>
    </template>
  </UModal>
</template>
