<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import type { DropdownMenuItem } from '@nuxt/ui'
import WorkflowCrudPage from '@/shared/ui/WorkflowCrudPage.vue'
import DirectionImportWizard from '@/modules/directions/components/DirectionImportWizard.vue'
import { usePermission } from '@/shared/composables/usePermission'
import { crudModules } from '@/shared/config/crud-modules'
import type { CrudRow } from '@/shared/types/crud'

const { can } = usePermission()

const selectedConfig = crudModules.directions
const createDisabled = computed(() => !can(selectedConfig.resource, 'create'))
const importDisabled = computed(() => !can(selectedConfig.resource, 'import'))
const createMenuDisabled = computed(() => createDisabled.value && importDisabled.value)

const importWizardOpen = ref(false)
// Направление, для которого мастер открыт в режиме «существующий черновик»
// (пусто — свежий импорт из файла).
const wizardDirectionId = ref<string | null>(null)
// Id, вернувшийся из мастера по завершении (для свежего импорта — первый черновик).
const finishedDirectionId = ref<string | null>(null)

// Кратковременная подсветка затронутой строки в таблице после закрытия мастера.
const highlightId = ref<string | null>(null)
let highlightTimer: ReturnType<typeof setTimeout> | null = null

const highlightDirection = (id: string | null) => {
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

onBeforeUnmount(() => {
  if (highlightTimer) {
    clearTimeout(highlightTimer)
  }
})

const openImportWizard = () => {
  wizardDirectionId.value = null
  importWizardOpen.value = true
}

const openDraftWizard = (row: CrudRow) => {
  wizardDirectionId.value = String(row.id)
  importWizardOpen.value = true
}

// Кастомное действие строки: только для draft-направлений и при праве на правку.
const rowActions = (row: CrudRow): DropdownMenuItem[] => {
  const code = (row.status as { code?: string } | null | undefined)?.code
  if (code !== 'draft' || !can(selectedConfig.resource, 'edit')) {
    return []
  }
  return [
    {
      label: 'Дозаполнить / Открыть мастер',
      icon: 'i-lucide-pencil-ruler',
      onSelect: () => openDraftWizard(row),
    },
  ]
}

const onWizardFinished = (id: string | null) => {
  finishedDirectionId.value = id
}

// Любое закрытие мастера обновляет таблицу; при известном id — подсвечиваем строку.
const onWizardOpenChange = (value: boolean, refresh: () => void) => {
  importWizardOpen.value = value
  if (value) {
    return
  }
  const affectedId = wizardDirectionId.value ?? finishedDirectionId.value
  refresh()
  highlightDirection(affectedId)
  wizardDirectionId.value = null
  finishedDirectionId.value = null
}
</script>

<template>
  <WorkflowCrudPage
    :config="selectedConfig"
    panel-id="directions"
    title="Направления"
    search-placeholder="Поиск по направлениям"
    :extra-row-actions="rowActions"
    :highlight-id="highlightId"
  >
    <template #navbar-right="{ openCreate, refresh }">
      <div class="flex items-center gap-2">
        <UTooltip :text="importDisabled ? 'Нет прав на импорт' : 'Пошаговый импорт направлений'">
          <UButton
            label="Импорт направлений"
            :icon="importDisabled ? 'i-lucide-lock' : 'i-lucide-file-up'"
            color="neutral"
            variant="outline"
            :disabled="importDisabled"
            data-testid="direction-import-open"
            data-telemetry="direction-import-open"
            @click="openImportWizard()"
          />
        </UTooltip>
        <UTooltip :text="createMenuDisabled ? 'Нет прав на создание' : 'Создать направление'">
          <UButton
            label="Создать"
            :icon="createDisabled ? 'i-lucide-lock' : 'i-lucide-plus'"
            :disabled="createDisabled"
            @click="openCreate()"
          />
        </UTooltip>
      </div>

      <DirectionImportWizard
        :open="importWizardOpen"
        :direction-id="wizardDirectionId"
        @update:open="(value: boolean) => onWizardOpenChange(value, refresh)"
        @finished="onWizardFinished"
      />
    </template>
  </WorkflowCrudPage>
</template>
