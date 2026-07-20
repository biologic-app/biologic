<script setup lang="ts">
import { useI18n } from "vue-i18n";
import WorkflowCrudPage from "@/shared/ui/WorkflowCrudPage.vue";
import { crudModules } from "@/shared/config/crud-modules";

const selectedConfig = crudModules.tests;
const { t } = useI18n();
</script>

<template>
  <WorkflowCrudPage
    :config="selectedConfig"
    panel-id="tests"
    :title="t('nav.tests')"
    :search-placeholder="t('directionWizard.searchTests')"
    :show-sidebar-collapse="false"
  />
</template>
