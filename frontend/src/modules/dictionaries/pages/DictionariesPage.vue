<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import type { NavigationMenuItem } from "@nuxt/ui";
import {
  defaultDictionaryKey,
  dictionaryItems,
  getDictionaryConfig,
  getDictionaryItem,
  isDictionaryKey,
  statusDictionaryItems,
} from "@/modules/dictionaries/config";
import DictionaryCrudContent from "@/modules/dictionaries/pages/DictionaryCrudContent.vue";
import NotificationsBellButton from "@/shared/ui/NotificationsBellButton.vue";
import { usePermission } from "@/shared/composables/usePermission";
import CrudSearchControl from "@/shared/ui/CrudSearchControl.vue";

const route = useRoute();
const router = useRouter();
const { can } = usePermission();
const { t } = useI18n();
const crudContent = ref<InstanceType<typeof DictionaryCrudContent> | null>(null);
const tableSearch = ref("");
const refreshToken = ref(0);

// Кнопка «Обновить» — перезагрузка данных таблицы через метод дочернего CRUD.
const refresh = () => crudContent.value?.refresh();

const moduleKey = computed(() => {
  const rawModule = route.params.module;
  const key = Array.isArray(rawModule) ? rawModule[0] : rawModule;
  return key || defaultDictionaryKey;
});

const selectedItem = computed(
  () => getDictionaryItem(moduleKey.value) || dictionaryItems[0],
);

const selectedConfig = computed(() => getDictionaryConfig(selectedItem.value));

const dictionaryLinks = computed<NavigationMenuItem[][]>(() => [
  [
    ...dictionaryItems.map((item) => ({
      label: item.label,
      icon: item.icon,
      to:
        item.key === "statuses"
          ? "/dictionaries/statuses"
          : `/dictionaries/${item.key}`,
      active:
        item.key === "statuses"
          ? selectedItem.value.key === "statuses" || selectedItem.value.key.startsWith("statuses-")
          : selectedItem.value.key === item.key,
      exact: true,
    })),
  ],
]);

const statusLinks = computed<NavigationMenuItem[][]>(() => [
  statusDictionaryItems.map((item) => ({
    label: item.label,
    icon: item.icon,
    to: `/dictionaries/${item.key}`,
    exact: true,
  })),
]);

const showStatusNavigation = computed(
  () => selectedItem.value.key === "statuses" || selectedItem.value.key.startsWith("statuses-"),
);

const createDisabled = computed(() => !can(selectedConfig.value.resource, "create"));

watch(
  moduleKey,
  (key) => {
    if (!isDictionaryKey(key)) {
      router.replace(`/dictionaries/${defaultDictionaryKey}`);
      return;
    }

    if (key === "statuses") {
      router.replace(`/dictionaries/${statusDictionaryItems[0].key}`);
    }
  },
  { immediate: true },
);

</script>

<template>
  <UDashboardPanel id="dictionaries" :ui="{ body: 'min-h-0 overflow-hidden' }">
    <template #header>
      <UDashboardNavbar :title="t('dictionaries.title')">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <UTooltip :text="createDisabled ? t('dictionaries.noCreatePermission') : t('dictionaries.createRecord')">
            <UButton
              :label="t('common.create')"
              :icon="createDisabled ? 'i-lucide-lock' : 'i-lucide-plus'"
              :disabled="createDisabled"
              @click="crudContent?.openCreate()"
            />
          </UTooltip>

          <NotificationsBellButton />
        </template>
      </UDashboardNavbar>

      <UDashboardToolbar>
        <UNavigationMenu :items="dictionaryLinks" highlight class="-mx-1 flex-1" />
      </UDashboardToolbar>

      <UDashboardToolbar v-if="showStatusNavigation">
        <UNavigationMenu :items="statusLinks" highlight class="-mx-1 flex-1" />
      </UDashboardToolbar>

      <UDashboardToolbar>
        <template #left>
          <div class="flex w-full flex-col gap-3 lg:flex-row lg:items-center">
            <CrudSearchControl v-model="tableSearch" :placeholder="t('dictionaries.searchPlaceholder')" />
          </div>
        </template>
        <template #right>
          <div class="flex flex-wrap items-center gap-2">
            <UButton
              v-show="crudContent?.selectedCount"
              color="error"
              variant="subtle"
              icon="i-lucide-trash"
              :label="t('common.delete')"
              @click="crudContent?.deleteSelected()"
            >
              <template #trailing>
                <UKbd>{{ crudContent?.selectedCount }}</UKbd>
              </template>
            </UButton>
            <UTooltip :text="t('access.refreshData')">
              <UButton
                :label="t('common.update')"
                color="neutral"
                variant="subtle"
                icon="i-lucide-refresh-cw"
                @click="refresh"
              />
            </UTooltip>

            <UDropdownMenu :items="crudContent?.columnMenuItems || []" :content="{ align: 'end' }">
              <UTooltip :text="t('access.tableColumns')">
                <UButton color="neutral" variant="subtle" trailing-icon="i-lucide-settings-2" />
              </UTooltip>
            </UDropdownMenu>
          </div>
        </template>
      </UDashboardToolbar>
    </template>

    <template #body>
      <div class="flex min-h-0 w-full flex-1 flex-col gap-4">
        <DictionaryCrudContent
          ref="crudContent"
          :key="moduleKey"
          :config="selectedConfig"
          :request-params="selectedItem.requestParams"
          :search="tableSearch"
          :refresh-token="refreshToken"
        />
      </div>
    </template>
  </UDashboardPanel>
</template>
