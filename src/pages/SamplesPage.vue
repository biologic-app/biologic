<script setup lang="ts">
import { computed, ref } from "vue";
import DictionaryCrudContent from "@/modules/dictionaries/pages/DictionaryCrudContent.vue";
import { usePermission } from "@/shared/composables/usePermission";
import CrudFilterControls from "@/shared/ui/CrudFilterControls.vue";
import CrudSearchControl from "@/shared/ui/CrudSearchControl.vue";
import { crudModules } from "@/shared/config/crud-modules";

const { can } = usePermission();
const crudContent = ref<InstanceType<typeof DictionaryCrudContent> | null>(null);
const tableSearch = ref("");
const filterModalOpen = ref(false);
const refreshToken = ref(0);
const resetToken = ref(0);

const selectedConfig = crudModules.samples;

const createDisabled = !can(selectedConfig.resource, "create");
const activeFilterCount = computed(() => crudContent.value?.activeFilterCount || 0);
</script>

<template>
  <UDashboardPanel id="samples" :ui="{ body: 'min-h-0 overflow-hidden' }">
    <template #header>
      <UDashboardNavbar title="Образцы">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <UTooltip :text="createDisabled ? 'Нет прав на создание' : 'Создать запись'">
            <UButton label="Создать" :icon="createDisabled ? 'i-lucide-lock' : 'i-lucide-plus'"
              :disabled="createDisabled" @click="crudContent?.openCreate()" />
          </UTooltip>
        </template>
      </UDashboardNavbar>

      <UDashboardToolbar>
        <template #left>
          <div class="flex w-full flex-col gap-3 lg:flex-row lg:items-center">
            <CrudSearchControl v-model="tableSearch" placeholder="Поиск по образцам" />
            <CrudFilterControls :active-count="activeFilterCount" @open="filterModalOpen = true"
              @clear="resetToken++" />
          </div>
        </template>
        <template #right>
          <div class="flex flex-wrap items-center gap-2">
            <UButton v-show="crudContent?.selectedCount" :disabled="!crudContent?.canRegisterSelectedSamples"
              color="primary" variant="subtle" icon="i-lucide-clipboard-check" label="Зарегистрировать"
              @click="crudContent?.registerSelectedSamples()">
              <template #trailing>
                <UKbd>{{ crudContent?.selectedCount }}</UKbd>
              </template>
            </UButton>
            <UButton v-show="crudContent?.selectedCount" :disabled="!crudContent?.canRejectSelectedSamples"
              color="warning" variant="subtle" icon="i-lucide-ban" label="Брак"
              @click="crudContent?.rejectSelectedSamples()">
              <template #trailing>
                <UKbd>{{ crudContent?.selectedCount }}</UKbd>
              </template>
            </UButton>
            <UButton v-show="crudContent?.selectedCount" :disabled="!crudContent?.canCloseSelectedSamples"
              color="success" variant="subtle" icon="i-lucide-lock-keyhole" label="Закрыть"
              @click="crudContent?.closeSelectedSamples()">
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
          v-model:filter-open="filterModalOpen" :refresh-token="refreshToken" :reset-token="resetToken" />
      </div>
    </template>
  </UDashboardPanel>
</template>
