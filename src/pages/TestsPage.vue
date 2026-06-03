<script setup lang="ts">
import { computed, ref } from "vue";
import DictionaryCrudContent from "@/modules/dictionaries/pages/DictionaryCrudContent.vue";
import CrudFilterControls from "@/shared/ui/CrudFilterControls.vue";
import CrudSearchControl from "@/shared/ui/CrudSearchControl.vue";
import { crudModules } from "@/shared/config/crud-modules";

const crudContent = ref<InstanceType<typeof DictionaryCrudContent> | null>(null);
const tableSearch = ref("");
const refreshToken = ref(0);
const resetToken = ref(0);

const selectedConfig = crudModules.tests;
const activeFilterCount = computed(() => crudContent.value?.activeFilterCount || 0);
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
            <CrudFilterControls :active-count="activeFilterCount" @open="crudContent!.filterModalOpen = true"
              @clear="resetToken++" />
          </div>
        </template>
        <template #right>
          <div class="flex flex-wrap items-center gap-2">
            <UButton v-show="crudContent?.selectedCount" :disabled="!crudContent?.canStartSelectedTests" color="primary"
              variant="subtle" icon="i-lucide-play" label="В работу" @click="crudContent?.startSelectedTests()">
              <template #trailing>
                <UKbd>{{ crudContent?.selectedCount }}</UKbd>
              </template>
            </UButton>
            <UButton v-show="crudContent?.selectedCount" :disabled="!crudContent?.canCompleteSelectedTests"
              color="success" variant="subtle" icon="i-lucide-check" label="Результат"
              @click="crudContent?.completeSelectedTests()">
              <template #trailing>
                <UKbd>{{ crudContent?.selectedCount }}</UKbd>
              </template>
            </UButton>
            <UButton v-show="crudContent?.selectedCount" :disabled="!crudContent?.canRequeueSelectedTests"
              color="warning" variant="subtle" icon="i-lucide-rotate-ccw" label="В очередь"
              @click="crudContent?.requeueSelectedTests()">
              <template #trailing>
                <UKbd>{{ crudContent?.selectedCount }}</UKbd>
              </template>
            </UButton>
            <UButton v-show="crudContent?.selectedCount" :disabled="!crudContent?.canRejectSelectedTests" color="error"
              variant="subtle" icon="i-lucide-ban" label="Отклонить" @click="crudContent?.rejectSelectedTests()">
              <template #trailing>
                <UKbd>{{ crudContent?.selectedCount }}</UKbd>
              </template>
            </UButton>
            <UButton v-show="crudContent?.selectedCount" color="error" variant="subtle" icon="i-lucide-trash"
              label="Удалить" :disabled="!crudContent?.canDeleteSelected" @click="crudContent?.deleteSelected()">
              <template #trailing>
                <UKbd>{{ crudContent?.selectedCount }}</UKbd>
              </template>
            </UButton>
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
          :refresh-token="refreshToken" :reset-token="resetToken" />
      </div>
    </template>
  </UDashboardPanel>
</template>
