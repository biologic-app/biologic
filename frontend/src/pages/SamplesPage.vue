<script setup lang="ts">
import WorkflowCrudPage from "@/shared/ui/WorkflowCrudPage.vue";
import { crudModules } from "@/shared/config/crud-modules";

const selectedConfig = crudModules.samples;
</script>

<template>
  <WorkflowCrudPage
    :config="selectedConfig"
    panel-id="samples"
    title="Образцы"
    search-placeholder="Поиск по образцам"
  />
</template>
