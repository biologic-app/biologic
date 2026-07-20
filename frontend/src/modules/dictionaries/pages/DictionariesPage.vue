<script setup lang="ts">
import { computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import type { NavigationMenuItem } from "@nuxt/ui";
import {
  defaultDictionaryKey,
  dictionaryItems,
  getDictionaryConfig,
  getDictionaryItem,
  isDictionaryKey,
  statusDictionaryItems,
} from "@/modules/dictionaries/config";
import WorkflowCrudPage from "@/shared/ui/WorkflowCrudPage.vue";
import { usePermission } from "@/shared/composables/usePermission";

const route = useRoute();
const router = useRouter();
const { can } = usePermission();

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
  <!-- Ключ по модулю: смена справочника пересобирает таблицу (сброс поиска/
       фильтров/состояния колонок), как раньше делал :key на контенте. -->
  <WorkflowCrudPage
    :key="moduleKey"
    :config="selectedConfig"
    panel-id="dictionaries"
    title="Справочники"
    search-placeholder="Поиск по справочнику"
  >
    <template #navbar-right="{ openCreate }">
      <UTooltip :text="createDisabled ? 'Нет прав на создание' : 'Создать запись'">
        <UButton
          label="Создать"
          :icon="createDisabled ? 'i-lucide-lock' : 'i-lucide-plus'"
          :disabled="createDisabled"
          @click="openCreate()"
        />
      </UTooltip>
    </template>

    <template #toolbar-extra>
      <UDashboardToolbar>
        <UNavigationMenu :items="dictionaryLinks" highlight class="-mx-1 flex-1" />
      </UDashboardToolbar>

      <UDashboardToolbar v-if="showStatusNavigation">
        <UNavigationMenu :items="statusLinks" highlight class="-mx-1 flex-1" />
      </UDashboardToolbar>
    </template>
  </WorkflowCrudPage>
</template>
