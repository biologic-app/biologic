<script setup lang="ts">
import { computed, ref } from 'vue'
import WorkflowCrudPage from '@/shared/ui/WorkflowCrudPage.vue'
import DirectionImportWizard from '@/modules/directions/components/DirectionImportWizard.vue'
import { usePermission } from '@/shared/composables/usePermission'
import { crudModules } from '@/shared/config/crud-modules'

const { can } = usePermission()

const selectedConfig = crudModules.directions
const createDisabled = computed(() => !can(selectedConfig.resource, 'create'))
const importDisabled = computed(() => !can(selectedConfig.resource, 'import'))
const createMenuDisabled = computed(() => createDisabled.value && importDisabled.value)

const importWizardOpen = ref(false)

const openImportWizard = () => {
  importWizardOpen.value = true
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

      <DirectionImportWizard v-model:open="importWizardOpen" @finished="refresh()" />
    </template>
  </WorkflowCrudPage>
</template>
