<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import type { DropdownMenuItem } from '@nuxt/ui'
import WorkflowCrudPage from '@/shared/ui/WorkflowCrudPage.vue'
import DirectionWizard from '@/modules/directions/components/DirectionWizard.vue'
import ReleasedSamplesByDirectionModal from '@/shared/ui/ReleasedSamplesByDirectionModal.vue'
import { usePermission } from '@/shared/composables/usePermission'
import { crudModules } from '@/shared/config/crud-modules'
import type { CrudRow } from '@/shared/types/crud'

const { can } = usePermission()

const selectedConfig = crudModules.directions
const createDisabled = computed(() => !can(selectedConfig.resource, 'create'))
const importDisabled = computed(() => !can(selectedConfig.resource, 'import'))
const createMenuDisabled = computed(() => createDisabled.value && importDisabled.value)

// Модалка «Выпущенные образцы по направлениям» — доступна регистратору
// (право protocols:create) или всем, кто видит образцы.
const releasedOpen = ref(false)
const canViewReleased = computed(() => can('protocols', 'create') || can('samples', 'view'))

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

// Единый мастер создания: открывается на экране выбора режима (импорт / вручную).
const openCreateWizard = () => {
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
    <template #navbar-right="{ refresh }">
      <div class="flex items-center gap-2">
        <UButton
          v-if="canViewReleased"
          label="Выпущенные образцы"
          icon="i-lucide-package-check"
          color="neutral"
          variant="subtle"
          data-testid="open-released-samples"
          data-telemetry="directions-open-released-samples"
          @click="releasedOpen = true"
        />
        <UTooltip :text="createMenuDisabled ? 'Нет прав на создание' : 'Создать направление (импорт или вручную)'">
          <UButton
            label="Создать направление"
            :icon="createMenuDisabled ? 'i-lucide-lock' : 'i-lucide-plus'"
            :disabled="createMenuDisabled"
            data-testid="direction-create-open"
            data-telemetry="direction-create-open"
            @click="openCreateWizard()"
          />
        </UTooltip>
      </div>

      <ReleasedSamplesByDirectionModal v-model:open="releasedOpen" />

      <DirectionWizard
        :open="importWizardOpen"
        :direction-id="wizardDirectionId"
        :can-import="!importDisabled"
        :can-create="!createDisabled"
        @update:open="(value: boolean) => onWizardOpenChange(value, refresh)"
        @finished="onWizardFinished"
      />
    </template>
  </WorkflowCrudPage>
</template>
