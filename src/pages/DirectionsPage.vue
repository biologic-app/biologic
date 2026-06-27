<script setup lang="ts">
import { computed, ref } from 'vue'
import WorkflowCrudPage from '@/shared/ui/WorkflowCrudPage.vue'
import { usePermission } from '@/shared/composables/usePermission'
import { apiUploadRequest } from '@/shared/api/client.api'
import { crudModules } from '@/shared/config/crud-modules'

const { can } = usePermission()
const toast = useToast()
const importInput = ref<HTMLInputElement | null>(null)
const importing = ref(false)

const selectedConfig = crudModules.directions
const createDisabled = computed(() => !can(selectedConfig.resource, 'create'))
const importDisabled = computed(() => !can(selectedConfig.resource, 'import'))
const createMenuDisabled = computed(() => createDisabled.value && importDisabled.value)

interface DirectionImportSummary {
  filename: string
  processed: number
  imported: number
  skipped: number
  errors: Array<Record<string, unknown>>
  warnings: Array<Record<string, unknown>>
}

const buildCreateMenu = (openCreate: () => void) => [
  {
    label: 'Импортировать CSV',
    icon: importDisabled.value ? 'i-lucide-lock' : 'i-lucide-upload',
    disabled: importDisabled.value || importing.value,
    onSelect() {
      importInput.value?.click()
    }
  }
]

const handleImportFile = async (event: Event, refresh: () => void) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || importDisabled.value || importing.value) {
    return
  }

  importing.value = true
  try {
    const response = await apiUploadRequest<DirectionImportSummary>('/directions/import', file)
    toast.add({
      title: 'Импорт направлений завершён',
      description: `Добавлено: ${response.data.imported}, пропущено: ${response.data.skipped}`,
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
        ref="importInput"
        type="file"
        accept=".csv,text/csv"
        class="hidden"
        @change="handleImportFile($event, refresh)"
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
          
          <UButton variant="outline" icon="i-lucide-chevron-down" />
        </UDropdownMenu>
      </UFieldGroup>
      
    </template>
  </WorkflowCrudPage>
</template>
