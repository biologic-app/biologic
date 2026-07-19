<script setup lang="ts">
import { computed } from "vue";
import WorkflowCrudPage from "@/shared/ui/WorkflowCrudPage.vue";
import AccessNavigation from "@/modules/access/components/AccessNavigation.vue";
import { usePermission } from "@/shared/composables/usePermission";
import { crudModules } from "@/shared/config/crud-modules";

const { can } = usePermission();

// Правила подписки по ролям — часть домена доступа (resource: user-types),
// поэтому страница живёт в группе «Доступ» и наследует стиль «Направлений».
const selectedConfig = crudModules["role-subscription-rules"];
const createDisabled = computed(() => !can(selectedConfig.resource, "create"));
</script>

<template>
  <WorkflowCrudPage
    :config="selectedConfig"
    panel-id="access-subscriptions"
    title="Доступ"
    search-placeholder="Поиск по правилам подписки"
  >
    <template #navbar-right="{ openCreate }">
      <UTooltip :text="createDisabled ? 'Нет прав на создание' : 'Создать правило подписки'">
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
        <AccessNavigation />
      </UDashboardToolbar>
    </template>
  </WorkflowCrudPage>
</template>
