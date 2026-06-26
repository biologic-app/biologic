<script setup lang="ts">
import { computed, ref } from 'vue'
import DictionaryCrudContent from '@/modules/dictionaries/pages/DictionaryCrudContent.vue'
import { usePermission } from '@/shared/composables/usePermission'
import { apiUploadRequest } from '@/shared/api/client.api'
import CrudFilterControls from '@/shared/ui/CrudFilterControls.vue'
import CrudSearchControl from '@/shared/ui/CrudSearchControl.vue'
import SelectionActionBar from '@/shared/ui/SelectionActionBar.vue'
import type { SelectionAction } from '@/shared/ui/SelectionActionBar.vue'
import { crudModules } from '@/shared/config/crud-modules'

const { can } = usePermission()
const toast = useToast()
const crudContent = ref<InstanceType<typeof DictionaryCrudContent> | null>(null)
const importInput = ref<HTMLInputElement | null>(null)
const tableSearch = ref('')
const filterModalOpen = ref(false)
const refreshToken = ref(0)
const resetToken = ref(0)
const importing = ref(false)

const selectedConfig = crudModules.directions
const createDisabled = computed(() => !can(selectedConfig.resource, 'create'))
const importDisabled = computed(() => !can(selectedConfig.resource, 'import'))
const createMenuDisabled = computed(() => createDisabled.value && importDisabled.value)
const activeFilterCount = computed(() => crudContent.value?.activeFilterCount || 0)
const selectedCount = computed(() => crudContent.value?.selectedCount ?? 0)

const selectionActions = computed<SelectionAction[]>(() => [
  {
    label: 'Зарегистрировать',
    icon: 'i-lucide-clipboard-check',
    color: 'primary',
    disabled: !crudContent.value?.canRegisterSelectedDirections,
    onClick: () => crudContent.value?.registerSelectedDirections(),
  },
  {
    label: 'Удалить',
    icon: 'i-lucide-trash',
    color: 'error',
    disabled: !crudContent.value?.canDeleteSelected,
    onClick: () => crudContent.value?.deleteSelected(),
  },
])

interface DirectionImportSummary {
  filename: string
  processed: number
  imported: number
  skipped: number
  errors: Array<Record<string, unknown>>
  warnings: Array<Record<string, unknown>>
}

const createMenuItems = computed(() => [
  {
    label: 'Создать вручную',
    icon: createDisabled.value ? 'i-lucide-lock' : 'i-lucide-plus',
    disabled: createDisabled.value,
    onSelect() {
      crudContent.value?.openCreate()
    }
  },
  {
    label: 'Импортировать CSV',
    icon: importDisabled.value ? 'i-lucide-lock' : 'i-lucide-upload',
    disabled: importDisabled.value || importing.value,
    onSelect() {
      importInput.value?.click()
    }
  }
])

const handleImportFile = async (event: Event) => {
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
    refreshToken.value += 1
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
  <UDashboardPanel id="directions" :ui="{ body: 'min-h-0 overflow-hidden' }">
    <template #header>
      <UDashboardNavbar title="Направления">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <input
            ref="importInput"
            type="file"
            accept=".csv,text/csv"
            class="hidden"
            @change="handleImportFile"
          >
          <UDropdownMenu
            :items="createMenuItems"
            :content="{ align: 'end' }"
          >
            <UTooltip :text="createMenuDisabled ? 'Нет прав на создание или импорт' : 'Создать или импортировать'">
              <UButton
                label="Создать"
                :icon="createMenuDisabled ? 'i-lucide-lock' : 'i-lucide-plus'"
                trailing-icon="i-lucide-chevron-down"
                :disabled="createMenuDisabled"
                :loading="importing"
              />
            </UTooltip>
          </UDropdownMenu>
        </template>
      </UDashboardNavbar>

      <UDashboardToolbar>
        <template #left>
          <div class="flex w-full flex-col gap-3 lg:flex-row lg:items-center">
            <CrudSearchControl
              v-model="tableSearch"
              placeholder="Поиск по направлениям"
            />
            <CrudFilterControls
              :active-count="activeFilterCount"
              @open="filterModalOpen = true"
              @clear="resetToken++"
            />
          </div>
        </template>
        <template #right>
          <div class="flex items-center gap-2">
            <UTooltip text="Обновить данные">
              <UButton
                color="neutral"
                variant="subtle"
                icon="i-lucide-refresh-cw"
                @click="refreshToken++"
              />
            </UTooltip>
            <UDropdownMenu
              :items="crudContent?.columnMenuItems || []"
              :content="{ align: 'end' }"
            >
              <UTooltip text="Столбцы таблицы">
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
        <DictionaryCrudContent
          ref="crudContent"
          v-model:filter-open="filterModalOpen"
          :config="selectedConfig"
          :search="tableSearch"
          :refresh-token="refreshToken"
          :reset-token="resetToken"
        />
      </div>
    </template>
  </UDashboardPanel>
</template>
