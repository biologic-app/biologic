<script setup lang="ts">
import { computed, ref } from "vue";
import type { DropdownMenuItem } from "@nuxt/ui";
import DictionaryCrudContent from "@/modules/dictionaries/pages/DictionaryCrudContent.vue";
import CrudFilterControls from "@/shared/ui/CrudFilterControls.vue";
import CrudSearchControl from "@/shared/ui/CrudSearchControl.vue";
import type { CrudModuleConfig, CrudRow } from "@/shared/types/crud";

// Декларативный хост страницы рабочих процессов: панель + тулбар (поиск,
// фильтры, обновление, столбцы) + DictionaryCrudContent. Конкретные страницы
// передают config и при необходимости свои действия навбара через #navbar-right.
withDefaults(
  defineProps<{
    config: CrudModuleConfig;
    panelId: string;
    title: string;
    searchPlaceholder?: string;
    showSidebarCollapse?: boolean;
    extraRowActions?: (row: CrudRow) => DropdownMenuItem[];
    highlightId?: string | null;
  }>(),
  {
    searchPlaceholder: undefined,
    showSidebarCollapse: true,
    extraRowActions: undefined,
    highlightId: null,
  },
);

const crudContent = ref<InstanceType<typeof DictionaryCrudContent> | null>(null);
const tableSearch = ref("");
const filterModalOpen = ref(false);
const refreshToken = ref(0);
const resetToken = ref(0);

const activeFilterCount = computed(() => crudContent.value?.activeFilterCount || 0);
const columnMenuItems = computed(() => crudContent.value?.columnMenuItems || []);

const openCreate = () => crudContent.value?.openCreate();
const refresh = () => {
  refreshToken.value += 1;
};
</script>

<template>
  <UDashboardPanel :id="panelId" :ui="{ body: 'min-h-0 overflow-hidden' }">
    <template #header>
      <UDashboardNavbar :title="title">
        <template v-if="showSidebarCollapse" #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <slot name="navbar-right" :open-create="openCreate" :refresh="refresh" />
        </template>
      </UDashboardNavbar>

      <UDashboardToolbar>
        <template #left>
          <div class="flex w-full flex-col gap-3 lg:flex-row lg:items-center">
            <CrudSearchControl
              v-model="tableSearch"
              :placeholder="searchPlaceholder"
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
                label="Обновить"
                color="neutral"
                variant="subtle"
                icon="i-lucide-refresh-cw"
                @click="refresh"
              />
            </UTooltip>
            <UDropdownMenu :items="columnMenuItems" :content="{ align: 'end' }">
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
          :config="config"
          :search="tableSearch"
          :refresh-token="refreshToken"
          :reset-token="resetToken"
          :extra-row-actions="extraRowActions"
          :highlight-id="highlightId"
        />
      </div>
    </template>
  </UDashboardPanel>
</template>
