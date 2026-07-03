<script setup lang="ts">
import WorkflowCrudPage from "@/shared/ui/WorkflowCrudPage.vue";
import { crudModules } from "@/shared/config/crud-modules";

const selectedConfig = crudModules.protocols;
</script>

<template>
  <WorkflowCrudPage
    :config="selectedConfig"
    panel-id="protocols"
    title="Протоколы"
    search-placeholder="Поиск по протоколам"
  />
</template>
