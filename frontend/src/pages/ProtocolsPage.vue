<script setup lang="ts">
import { useI18n } from "vue-i18n";
import WorkflowCrudPage from "@/shared/ui/WorkflowCrudPage.vue";
import { crudModules } from "@/shared/config/crud-modules";

const selectedConfig = crudModules.protocols;
const { t } = useI18n();
</script>

<template>
  <WorkflowCrudPage
    :config="selectedConfig"
    panel-id="protocols"
    :title="t('nav.protocols')"
    :search-placeholder="t('directionWizard.searchProtocols')"
  />
</template>
