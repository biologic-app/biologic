<script setup lang="ts">
// «Исследования V2» — таблица исследований как в первой версии и карточка при
// открытии, но вместо таба «Тесты» — вкладка «Рабочий процесс» (пошаговый
// воркфлоу-журнал, привязанный к исследованию).
import WorkflowCrudPage from '@/shared/ui/WorkflowCrudPage.vue'
import { crudModules } from '@/shared/config/crud-modules'

const selectedConfig = crudModules.research
</script>

<template>
  <WorkflowCrudPage
    :config="selectedConfig"
    panel-id="research-v2"
    title="Исследования V2"
    search-placeholder="Поиск по исследованиям"
    research-workflow
  />
</template>
