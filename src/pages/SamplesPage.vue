<script setup lang="ts">
import { computed } from "vue";
import WorkflowCrudPage from "@/shared/ui/WorkflowCrudPage.vue";
import { usePermission } from "@/shared/composables/usePermission";
import { crudModules } from "@/shared/config/crud-modules";

const { can } = usePermission();
const selectedConfig = crudModules.samples;
const createDisabled = computed(() => !can(selectedConfig.resource, "create"));
</script>

<template>
  <WorkflowCrudPage
    :config="selectedConfig"
    panel-id="samples"
    title="Образцы"
    search-placeholder="Поиск по образцам"
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
  </WorkflowCrudPage>
</template>
