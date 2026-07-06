<script setup lang="ts">
import { computed, ref } from 'vue'
import WorkflowCrudPage from '@/shared/ui/WorkflowCrudPage.vue'
import { usePermission } from '@/shared/composables/usePermission'
import { apiCommandRequest } from '@/shared/api/client.api'
import { crudModules } from '@/shared/config/crud-modules'

const { can } = usePermission()
const toast = useToast()
const importExcelInput = ref<HTMLInputElement | null>(null)
const importJsonInput = ref<HTMLInputElement | null>(null)
const importing = ref(false)

const selectedConfig = crudModules.directions
const createDisabled = computed(() => !can(selectedConfig.resource, 'create'))
const importDisabled = computed(() => !can(selectedConfig.resource, 'import'))
const createMenuDisabled = computed(() => createDisabled.value && importDisabled.value)

// Единый DTO ответа POST /directions/import (см. backend WorkflowImportSummary) —
// один и тот же для xlsx/.xls и json.
interface WorkflowImportSummary {
  filename: string
  directions_created: number
  samples_created: number
  research_created: number
  skipped: number
  errors: Array<Record<string, unknown>>
  warnings: Array<Record<string, unknown>>
}

type ImportType = 'xlsx' | 'json'

const buildCreateMenu = () => [
  {
    label: 'Импортировать Excel',
    icon: importDisabled.value ? 'i-lucide-lock' : 'i-lucide-file-spreadsheet',
    disabled: importDisabled.value || importing.value,
    onSelect() {
      importExcelInput.value?.click()
    }
  },
  {
    label: 'Импортировать JSON',
    icon: importDisabled.value ? 'i-lucide-lock' : 'i-lucide-file-json',
    disabled: importDisabled.value || importing.value,
    onSelect() {
      importJsonInput.value?.click()
    }
  }
]

const runImport = async (file: File, type: ImportType, refresh: () => void) => {
  importing.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('type', type)
    const response = await apiCommandRequest<WorkflowImportSummary>('/directions/import', {
      method: 'POST',
      body: formData
    })
    toast.add({
      title: 'Импорт направлений завершён',
      description: `Направлений: ${response.data.directions_created}, образцов: ${response.data.samples_created}, исследований: ${response.data.research_created}, пропущено: ${response.data.skipped}`,
      color: response.data.errors.length ? 'warning' : 'success',
      icon: response.data.errors.length ? 'i-lucide-triangle-alert' : 'i-lucide-circle-check'
    })
    refresh()
  } catch (error) {
    const message = typeof error === 'object' && error !== null && 'message' in error
      ? String(error.message)
      : 'Проверьте файл и повторите импорт.'
    toast.add({
      title: 'Не удалось импортировать направления',
      description: message,
      color: 'error',
      icon: 'i-lucide-circle-alert'
    })
  } finally {
    importing.value = false
  }
}

const handleImportFile = (type: ImportType) => async (event: Event, refresh: () => void) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || importDisabled.value || importing.value) {
    return
  }
  await runImport(file, type, refresh)
}

const handleImportExcelFile = handleImportFile('xlsx')
const handleImportJsonFile = handleImportFile('json')
</script>

<template>
  <WorkflowCrudPage
    :config="selectedConfig"
    panel-id="directions"
    title="Направления"
    search-placeholder="Поиск по направлениям"
  >
    <template #navbar-right="{ openCreate, refresh }">
      <input
        ref="importExcelInput"
        type="file"
        accept=".xls,.xlsx"
        class="hidden"
        data-testid="import-excel-input"
        @change="handleImportExcelFile($event, refresh)"
      >
      <input
        ref="importJsonInput"
        type="file"
        accept=".json"
        class="hidden"
        data-testid="import-json-input"
        @change="handleImportJsonFile($event, refresh)"
      >
      <UFieldGroup>
        <UTooltip :text="createMenuDisabled ? 'Нет прав на создание или импорт' : 'Создать или импортировать'">
          <UButton
            label="Создать"
            @click="openCreate()"
            :icon="createMenuDisabled ? 'i-lucide-lock' : 'i-lucide-plus'"
            :disabled="createMenuDisabled"
            :loading="importing"
          />
        </UTooltip>
        <UDropdownMenu
          :items="buildCreateMenu()"
          :content="{ align: 'end' }"
        >

          <UButton variant="outline" icon="i-lucide-chevron-down" data-testid="direction-import-menu-trigger" />
        </UDropdownMenu>
      </UFieldGroup>

    </template>
  </WorkflowCrudPage>
</template>
