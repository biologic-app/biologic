<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import WorkflowCrudPage from "@/shared/ui/WorkflowCrudPage.vue";
import { crudModules } from "@/shared/config/crud-modules";
import { registerTourAction } from "@/shared/tour/tour.actions";

const selectedConfig = crudModules.research;
const { t } = useI18n();

const workflowPage = ref<InstanceType<typeof WorkflowCrudPage> | null>(null);

let unregisterTourAction: (() => void) | null = null;
onMounted(() => {
  unregisterTourAction = registerTourAction("research-open-detail", () => {
    workflowPage.value?.openFirstRowDetail();
  });
});
onBeforeUnmount(() => {
  unregisterTourAction?.();
});
</script>

<template>
  <WorkflowCrudPage
    ref="workflowPage"
    :config="selectedConfig"
    panel-id="research"
    :title="t('nav.research')"
    :search-placeholder="t('directionWizard.searchResearch')"
    tour-scope="research"
  />
</template>
