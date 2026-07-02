<script setup lang="ts">
import { computed, ref } from 'vue'
import WorkflowCrudPage from '@/shared/ui/WorkflowCrudPage.vue'
import { usePermission } from '@/shared/composables/usePermission'
import { apiUploadRequest } from '@/shared/api/client.api'
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

interface WorkflowImportSummary {
  filename: string
  rows_processed: number
  directions_created: number
  samples_created: number
  skipped_rows: number
  errors: Array<Record<string, unknown>>
  warnings: Array<Record<string, unknown>>
}

const buildCreateMenu = (openCreate: () => void) => [
  {
    label: 'Импортировать Excel',
    icon: importDisabled.value ? 'i-lucide-lock' : 'i-lucide-file-spreadsheet',
    disabled: importDisabled.value || importing.value,
    onSelect() {
      importExcelInput.value?.click()
    }
  },
  {
    label: 'Импортировать JSON (резервный способ)',
    icon: importDisabled.value ? 'i-lucide-lock' : 'i-lucide-file-json',
    disabled: importDisabled.value || importing.value,
    onSelect() {
      importJsonInput.value?.click()
    }
  }
]

const handleImportFile = async (
  event: Event,
  refresh: () => void,
  endpoint: '/directions/import-excel' | '/directions/import-json'
) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || importDisabled.value || importing.value) {
    return
  }

  importing.value = true
  try {
    const response = await apiUploadRequest<WorkflowImportSummary>(endpoint, file)
    toast.add({
      title: 'Импорт направлений завершён',
      description: `Направлений: ${response.data.directions_created}, образцов: ${response.data.samples_created}, пропущено строк: ${response.data.skipped_rows}`,
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
        accept=".xlsx"
        class="hidden"
        data-testid="import-excel-input"
        @change="handleImportFile($event, refresh, '/directions/import-excel')"
      >
      <input
        ref="importJsonInput"
        type="file"
        accept=".json,application/json"
        class="hidden"
        data-testid="import-json-input"
        @change="handleImportFile($event, refresh, '/directions/import-json')"
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
          :items="buildCreateMenu(openCreate)"
          :content="{ align: 'end' }"
        >

          <UButton variant="outline" icon="i-lucide-chevron-down" data-testid="direction-import-menu-trigger" />
        </UDropdownMenu>
      </UFieldGroup>

    </template>
  </WorkflowCrudPage>
</template>
