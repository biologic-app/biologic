<script setup lang="ts">
import { computed, ref } from 'vue'
import DictionaryCrudContent from '@/modules/dictionaries/pages/DictionaryCrudContent.vue'
import { usePermission } from '@/shared/composables/usePermission'
import CrudFilterControls from '@/shared/ui/CrudFilterControls.vue'
import CrudSearchControl from '@/shared/ui/CrudSearchControl.vue'
import { crudModules } from '@/shared/config/crud-modules'

const { can } = usePermission()
const crudContent = ref<InstanceType<typeof DictionaryCrudContent> | null>(null)
const tableSearch = ref('')
const refreshToken = ref(0)
const resetToken = ref(0)

const selectedConfig = crudModules.research
const createDisabled = computed(() => !can(selectedConfig.resource, 'create'))
const activeFilterCount = computed(() => crudContent.value?.activeFilterCount || 0)
</script>

<template>
  <UDashboardPanel id="research" :ui="{ body: 'min-h-0 overflow-hidden' }">
    <template #header>
      <UDashboardNavbar title="Исследования">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <UTooltip :text="createDisabled ? 'Нет прав на создание' : 'Создать запись'">
            <UButton
              label="Создать"
              :icon="createDisabled ? 'i-lucide-lock' : 'i-lucide-plus'"
              :disabled="createDisabled"
              @click="crudContent?.openCreate()"
            />
          </UTooltip>
        </template>
      </UDashboardNavbar>

      <UDashboardToolbar>
        <template #left>
          <div class="flex w-full flex-col gap-3 lg:flex-row lg:items-center">
            <CrudSearchControl v-model="tableSearch" placeholder="Поиск по исследованиям" />
            <CrudFilterControls
              :active-count="activeFilterCount"
              @open="crudContent!.filterModalOpen = true"
              @clear="resetToken++"
            />
          </div>
        </template>
        <template #right>
          <div class="flex flex-wrap items-center gap-2">
            <UButton
              v-show="crudContent?.selectedCount"
              color="error"
              variant="subtle"
              icon="i-lucide-trash"
              label="Удалить"
              @click="crudContent?.deleteSelected()"
            >
              <template #trailing>
                <UKbd>{{ crudContent?.selectedCount }}</UKbd>
              </template>
            </UButton>
            <UButton
              color="neutral"
              variant="subtle"
              icon="i-lucide-refresh-cw"
              label="Обновить"
              @click="refreshToken++"
            />
            <UDropdownMenu :items="crudContent?.columnMenuItems || []" :content="{ align: 'end' }">
              <UButton
                label="Столбцы"
                color="neutral"
                variant="subtle"
                trailing-icon="i-lucide-settings-2"
              />
            </UDropdownMenu>
          </div>
        </template>
      </UDashboardToolbar>
    </template>

    <template #body>
      <div class="flex h-full min-h-0 w-full flex-col">
        <DictionaryCrudContent
          ref="crudContent"
          :config="selectedConfig"
          :search="tableSearch"
          :refresh-token="refreshToken"
          :reset-token="resetToken"
        />
      </div>
    </template>
  </UDashboardPanel>
</template>
