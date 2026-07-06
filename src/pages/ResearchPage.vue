<script setup lang="ts">
import WorkflowCrudPage from "@/shared/ui/WorkflowCrudPage.vue";
import { crudModules } from "@/shared/config/crud-modules";

const selectedConfig = crudModules.research;
</script>

<template>
  <WorkflowCrudPage
    :config="selectedConfig"
    panel-id="research"
    title="Исследования"
    search-placeholder="Поиск по исследованиям"
  />
</template>
