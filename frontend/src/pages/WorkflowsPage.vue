<script setup lang="ts">
// Страница «Рабочие процессы» — master-detail: список журналов слева + живой
// канвас/раннер/карточка выбранного справа (US-канвас-редизайн). Модалка
// (WorkflowDetailModal) ретирована — её содержимое перенесено в правую панель.
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import type { DropdownMenuItem } from '@nuxt/ui'
import { useLocale } from '@/shared/composables/useLocale'
import type { FormField } from '@/shared/types/form'
import ConfirmDialog from '@/shared/ui/ConfirmDialog.vue'
import CrudFormModal from '@/shared/ui/CrudFormModal.vue'
import NotificationsBellButton from '@/shared/ui/NotificationsBellButton.vue'
import RowContextMenu from '@/shared/ui/RowContextMenu.vue'
import TourMenu from '@/shared/ui/TourMenu.vue'
import JournalBuilder from '@/modules/workflows/components/JournalBuilder.vue'
import WorkflowPreview from '@/modules/workflows/components/WorkflowPreview.vue'
import {
  countRunsByTemplate,
  createTemplate,
  deleteTemplate,
  getTemplate,
  importData,
  initDemoData,
  listTemplates,
  renameTemplate,
} from '@/modules/workflows/api/workflows.api'
import { fireSafety } from '@/modules/workflows/data/fire-safety'
import { labTestResult } from '@/modules/workflows/data/lab-test-result'
import { microbiologyStudy } from '@/modules/workflows/data/microbiology-study'
import { patientIntake } from '@/modules/workflows/data/patient-intake'
import { workflowCreation } from '@/modules/workflows/data/workflow-creation'
import type { JournalSchema, JournalTemplate } from '@/modules/workflows/types/journal'

const toast = useToast()
const { t } = useI18n()
const { intlLocale } = useLocale()
const route = useRoute()
const router = useRouter()

interface WorkflowRow {
  id: string
  title: string
  currentVersion: number
  entries: number
  updatedAt: string
}

const templates = ref<JournalTemplate[]>([])
// Число записей (runs) по каждому шаблону — один запрос вместо N+1 на строку.
const runCountByTemplate = ref<Record<string, number>>({})
const search = ref('')

async function refresh() {
  const [tpls, counts] = await Promise.all([listTemplates(), countRunsByTemplate()])
  templates.value = tpls
  runCountByTemplate.value = counts
}

onMounted(async () => {
  await initDemoData([workflowCreation, patientIntake, microbiologyStudy, labTestResult, fireSafety])
  await refresh()
  const routeId = typeof route.params.id === 'string' ? route.params.id : undefined
  if (routeId && templates.value.some((tpl) => tpl.id === routeId)) {
    selectedTemplateId.value = routeId
  } else if (templates.value.length) {
    selectedTemplateId.value = templates.value[0].id
  }
})

// Разовый импорт данных старого localStorage-конструктора в backend.
async function importFromLocalStorage() {
  const raw = typeof window !== 'undefined'
    ? localStorage.getItem('journal-constructor-storage')
    : null
  if (!raw) {
    toast.add({ title: 'В localStorage нет данных для импорта', color: 'warning', icon: 'i-lucide-info' })
    return
  }
  try {
    const summary = await importData(raw)
    await refresh()
    toast.add({
      title: `Импортировано шаблонов: ${summary.templates}, записей: ${summary.runs}`,
      color: 'success',
      icon: 'i-lucide-check',
    })
  } catch (error) {
    toast.add({
      title: 'Ошибка импорта из localStorage',
      description: (error as Error).message,
      color: 'error',
      icon: 'i-lucide-circle-alert',
    })
  }
}

const rows = computed<WorkflowRow[]>(() => {
  const query = search.value.trim().toLowerCase()
  return templates.value
    .filter((template) => !query || template.title.toLowerCase().includes(query))
    .map((template) => ({
      id: template.id,
      title: template.title,
      currentVersion: template.currentVersion,
      entries: runCountByTemplate.value[template.id] ?? 0,
      updatedAt: template.updatedAt,
    }))
    .sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : a.updatedAt > b.updatedAt ? -1 : 0))
})

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(intlLocale.value)
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

async function saveWorkflowForm(payload: Record<string, unknown>) {
  const title = String(payload.title ?? '').trim()
  if (!title) {
    return
  }

  if (formMode.value === 'edit' && formEditId.value) {
    await renameTemplate(formEditId.value, title)
    formModalOpen.value = false
    await refresh()
    toast.add({ title: t('workflows.toasts.renamed'), color: 'success', icon: 'i-lucide-check' })
    return
  }

  const schema: JournalSchema = {
    id: `template-${Date.now()}`,
    title,
    version: 1,
    nodes: [
      { id: 'start', type: 'start', position: { x: 80, y: 40 }, data: { label: 'Начало', trigger: 'manual' } },
      { id: 'end', type: 'end', position: { x: 80, y: 200 }, data: { label: 'Конец' } },
    ],
    edges: [{ id: 'e-start-end', source: 'start', target: 'end' }],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  }
  const template = await createTemplate(title, schema)
  formModalOpen.value = false
  await refresh()
  toast.add({ title: t('workflows.toasts.created'), color: 'success', icon: 'i-lucide-check' })
  selectTemplate(template.id)
}

// ─── Удаление ─────────────────────────────────────────────────────────────
const deleteOpen = ref(false)
const deleteRow = ref<WorkflowRow | null>(null)

function openDelete(row: WorkflowRow) {
  deleteRow.value = row
  deleteOpen.value = true
}

async function confirmDelete() {
  if (!deleteRow.value) {
    return
  }
  const wasSelected = deleteRow.value.id === selectedTemplateId.value
  await deleteTemplate(deleteRow.value.id)
  deleteOpen.value = false
  deleteRow.value = null
  await refresh()
  if (wasSelected) {
    selectTemplate(rows.value[0]?.id ?? null)
  }
  toast.add({ title: t('workflows.toasts.deleted'), color: 'success', icon: 'i-lucide-check' })
}

// ─── Действия по элементу списка ────────────────────────────────────────────
function itemActions(row: WorkflowRow): DropdownMenuItem[] {
  return [
    { label: t('workflows.actions.rename'), icon: 'i-lucide-pencil', onSelect: () => openRename(row) },
    { type: 'separator' },
    { label: t('workflows.actions.delete'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => openDelete(row) },
  ]
}

// Правый клик по элементу списка — то же меню, что у кнопки «⋯».
const contextRow = ref<WorkflowRow | null>(null)
const contextMenuOpen = ref(false)
const contextMenuPosition = ref({ x: 0, y: 0 })
const contextMenuItems = computed(() => (contextRow.value ? itemActions(contextRow.value) : []))

async function handleRowContextmenu(event: MouseEvent, row: WorkflowRow) {
  event.preventDefault()
  contextRow.value = row
  contextMenuOpen.value = false
  contextMenuPosition.value = { x: event.clientX, y: event.clientY }
  await nextTick()
  contextMenuOpen.value = true
}

// ─── Выбор процесса (master-detail) ────────────────────────────────────────
const selectedTemplateId = ref<string | null>(null)
const detailTemplate = ref<JournalTemplate | null>(null)
// Черновая схема канваса — синхронизируется с JournalBuilder (autosave) и
// кормит и «Тестовый прогон», и внутреннее состояние конструктора.
const builderSchema = ref<JournalSchema | null>(null)

watch(selectedTemplateId, async (id) => {
  detailTemplate.value = id ? (await getTemplate(id)) ?? null : null
})

watch(
  detailTemplate,
  (template) => {
    builderSchema.value = template ? template.versions[template.currentVersion - 1]?.schema ?? null : null
  },
  { immediate: true },
)

function selectTemplate(id: string | null) {
  selectedTemplateId.value = id
  void router.replace(id ? `/workflows/${id}` : '/workflows')
}

async function onVersionSaved(version: number) {
  await refresh()
  if (selectedTemplateId.value) {
    detailTemplate.value = (await getTemplate(selectedTemplateId.value)) ?? null
  }
  toast.add({ title: t('workflows.toasts.versionSaved', { version }), color: 'success', icon: 'i-lucide-check' })
}

// ─── Пробный запуск (Preview) — оверлей с живой черновой схемой ───────────
const previewOpen = ref(false)
// Изоляция: ключ = снимок схемы на момент открытия, чтобы движок Preview
// стартовал с чистого состояния на актуальных, в т.ч. несохранённых, нодах.
const previewKey = ref(0)
function openPreview() {
  previewKey.value += 1
  previewOpen.value = true
}

// Строка списка выбранного процесса — для переиспользования openRename/openDelete
// из шапки правой панели (см. rowActions в списке слева).
const selectedRow = computed<WorkflowRow | null>(() => rows.value.find((r) => r.id === selectedTemplateId.value) ?? null)
</script>

<template>
  <UDashboardPanel
    id="workflows-list"
    resizable
    :default-size="26"
    :min-size="20"
    :max-size="38"
    :ui="{ body: 'min-h-0 overflow-hidden p-0 sm:p-0' }"
  >
    <template #header>
      <UDashboardNavbar :title="t('workflows.title')">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <UButton
            :label="t('workflows.newProcess')"
            icon="i-lucide-plus"
            size="sm"
            @click="openCreate"
          />
          <NotificationsBellButton />
          <TourMenu scope="workflows" />
        </template>
      </UDashboardNavbar>

      <UDashboardToolbar>
        <template #left>
          <UInput
            v-model="search"
            icon="i-lucide-search"
            :placeholder="t('workflows.searchPlaceholder')"
            class="w-full"
          />
        </template>
        <template #right>
          <UTooltip :text="t('workflows.refresh')">
            <UButton
              :label="t('workflows.refresh')"
              icon="i-lucide-refresh-cw"
              color="neutral"
              variant="subtle"
              size="sm"
              @click="refresh"
            />
          </UTooltip>
          <UTooltip text="Импортировать процессы из старого localStorage в базу">
            <UButton
              icon="i-lucide-database-backup"
              color="neutral"
              variant="subtle"
              size="sm"
              @click="importFromLocalStorage"
            />
          </UTooltip>
        </template>
      </UDashboardToolbar>
    </template>

    <template #body>
      <div class="flex h-full min-h-0 flex-col">
        <div class="min-h-0 flex-1 overflow-y-auto">
          <div
            v-for="row in rows"
            :key="row.id"
            role="button"
            tabindex="0"
            class="group flex w-full items-center gap-2 border-b border-l-4 border-b-default/60 px-3 py-3 text-left transition-colors focus-visible:outline-2 focus-visible:outline-primary"
            :class="row.id === selectedTemplateId
              ? 'border-l-primary bg-primary/10'
              : 'border-l-transparent hover:bg-elevated'"
            @click="selectTemplate(row.id)"
            @keydown.enter="selectTemplate(row.id)"
            @contextmenu="handleRowContextmenu($event, row)"
          >
            <UIcon name="i-lucide-workflow" class="size-4 shrink-0 text-dimmed" />
            <span class="min-w-0 flex-1">
              <span class="block truncate text-sm font-medium text-highlighted">{{ row.title }}</span>
              <span class="mt-0.5 flex items-center gap-1.5 text-xs text-muted">
                <UBadge
                  color="neutral"
                  variant="subtle"
                  size="sm"
                  :label="t('workflows.version', { version: row.currentVersion })"
                />
                <span>{{ t('workflows.detail.entriesCount', { count: row.entries }) }}</span>
                <span class="ml-auto shrink-0">{{ formatDate(row.updatedAt) }}</span>
              </span>
            </span>
            <UDropdownMenu :items="itemActions(row)" :content="{ align: 'end' }" @click.stop>
              <UButton
                icon="i-lucide-ellipsis-vertical"
                color="neutral"
                variant="ghost"
                size="xs"
                class="opacity-0 group-hover:opacity-100"
                @click.stop
              />
            </UDropdownMenu>
          </div>

          <div v-if="!rows.length" class="p-6 text-center">
            <p class="text-sm font-medium text-highlighted">
              {{ t('workflows.empty.title') }}
            </p>
            <p class="mt-1 text-xs text-muted">
              {{ t('workflows.empty.description') }}
            </p>
          </div>
        </div>
      </div>
    </template>
  </UDashboardPanel>

  <RowContextMenu
    v-model:open="contextMenuOpen"
    :items="contextMenuItems"
    :x="contextMenuPosition.x"
    :y="contextMenuPosition.y"
  />

  <UDashboardPanel id="workflows-detail" class="hidden lg:flex" :ui="{ body: 'min-h-0 overflow-hidden p-0 sm:p-0' }">
    <template v-if="detailTemplate" #header>
      <UDashboardNavbar :title="detailTemplate.title">
        <template #right>
          <UButton
            :label="t('workflows.canvas.previewButton')"
            icon="i-lucide-flask-conical"
            color="primary"
            variant="soft"
            size="sm"
            @click="openPreview"
          />
          <UButton
            :label="t('workflows.actions.rename')"
            icon="i-lucide-pencil"
            color="neutral"
            variant="outline"
            size="sm"
            @click="selectedRow && openRename(selectedRow)"
          />
          <UButton
            :label="t('workflows.actions.delete')"
            icon="i-lucide-trash-2"
            color="error"
            variant="outline"
            size="sm"
            @click="selectedRow && openDelete(selectedRow)"
          />
        </template>
      </UDashboardNavbar>
    </template>

    <template #body>
      <div v-if="!detailTemplate" class="flex h-full items-center justify-center p-8">
        <p class="text-sm text-muted">
          {{ t('workflows.empty.description') }}
        </p>
      </div>

      <JournalBuilder
        v-else-if="builderSchema"
        :key="detailTemplate.id"
        v-model="builderSchema"
        :template-id="detailTemplate.id"
        @version-saved="onVersionSaved"
      />
    </template>
  </UDashboardPanel>

  <!-- Пробный запуск: живая черновая схема, ничего не пишет в БД -->
  <UModal
    v-model:open="previewOpen"
    :title="t('workflows.canvas.previewTitle')"
    :ui="{ content: 'max-w-[calc(100vw-4rem)] sm:max-w-6xl' }"
  >
    <template #body>
      <WorkflowPreview v-if="builderSchema" :key="previewKey" :schema="builderSchema" />
    </template>
  </UModal>

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
</template>
