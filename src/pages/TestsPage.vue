<script setup lang="ts">
import { computed, ref } from "vue";
import DictionaryCrudContent from "@/modules/dictionaries/pages/DictionaryCrudContent.vue";
import CrudFilterControls from "@/shared/ui/CrudFilterControls.vue";
import CrudSearchControl from "@/shared/ui/CrudSearchControl.vue";
import SelectionActionBar from "@/shared/ui/SelectionActionBar.vue";
import type { SelectionAction } from "@/shared/ui/SelectionActionBar.vue";
import { crudModules } from "@/shared/config/crud-modules";

const crudContent = ref<InstanceType<typeof DictionaryCrudContent> | null>(null);
const tableSearch = ref("");
const filterModalOpen = ref(false);
const refreshToken = ref(0);
const resetToken = ref(0);

const selectedConfig = crudModules.tests;
const activeFilterCount = computed(() => crudContent.value?.activeFilterCount || 0);
const selectedCount = computed(() => crudContent.value?.selectedCount ?? 0);

const selectionActions = computed<SelectionAction[]>(() => [
  {
    label: "В работу",
    icon: "i-lucide-play",
    color: "primary",
    disabled: !crudContent.value?.canStartSelectedTests,
    onClick: () => crudContent.value?.startSelectedTests(),
  },
  {
    label: "Результат",
    icon: "i-lucide-check",
    color: "success",
    disabled: !crudContent.value?.canCompleteSelectedTests,
    onClick: () => crudContent.value?.completeSelectedTests(),
  },
  {
    label: "В очередь",
    icon: "i-lucide-rotate-ccw",
    color: "warning",
    disabled: !crudContent.value?.canRequeueSelectedTests,
    onClick: () => crudContent.value?.requeueSelectedTests(),
  },
  {
    label: "Отклонить",
    icon: "i-lucide-ban",
    color: "error",
    disabled: !crudContent.value?.canRejectSelectedTests,
    onClick: () => crudContent.value?.rejectSelectedTests(),
  },
  {
    label: "Удалить",
    icon: "i-lucide-trash",
    color: "error",
    disabled: !crudContent.value?.canDeleteSelected,
    onClick: () => crudContent.value?.deleteSelected(),
  },
]);
</script>

<template>
  <UDashboardPanel id="tests" :ui="{ body: 'min-h-0 overflow-hidden' }">
    <template #header>
      <UDashboardNavbar title="Тесты">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
      </UDashboardNavbar>

      <UDashboardToolbar>
        <template #left>
          <div class="flex w-full flex-col gap-3 lg:flex-row lg:items-center">
            <CrudSearchControl v-model="tableSearch" placeholder="Поиск по тестам" />
            <CrudFilterControls :active-count="activeFilterCount" @open="filterModalOpen = true"
              @clear="resetToken++" />
          </div>
        </template>
        <template #right>
          <div class="flex items-center gap-2">
            <UTooltip text="Обновить данные">
              <UButton color="neutral" variant="subtle" icon="i-lucide-refresh-cw" @click="refreshToken++" />
            </UTooltip>
            <UDropdownMenu :items="crudContent?.columnMenuItems || []" :content="{ align: 'end' }">
              <UTooltip text="Столбцы таблицы">
                <UButton color="neutral" variant="subtle" trailing-icon="i-lucide-settings-2" />
              </UTooltip>
            </UDropdownMenu>
          </div>
        </template>
      </UDashboardToolbar>
    </template>

    <template #body>
      <div class="flex h-full min-h-0 w-full flex-col">
        <DictionaryCrudContent ref="crudContent" :config="selectedConfig" :search="tableSearch"
          v-model:filter-open="filterModalOpen" :refresh-token="refreshToken" :reset-token="resetToken" />
      </div>
    </template>
  </UDashboardPanel>

  <SelectionActionBar
    :count="selectedCount"
    :actions="selectionActions"
    @clear="crudContent?.clearSelection()"
  />
</template>
