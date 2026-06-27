<script setup lang="ts">
import WorkflowCrudPage from "@/shared/ui/WorkflowCrudPage.vue";
import { crudModules } from "@/shared/config/crud-modules";

const selectedConfig = crudModules.tests;
</script>

<template>
  <WorkflowCrudPage
    :config="selectedConfig"
    panel-id="tests"
    title="Тесты"
    search-placeholder="Поиск по тестам"
    :show-sidebar-collapse="false"
  />
</template>
