<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import WorkflowCrudPage from "@/shared/ui/WorkflowCrudPage.vue";
import { crudModules } from "@/shared/config/crud-modules";
import { registerTourAction } from "@/shared/tour/tour.actions";

const selectedConfig = crudModules.samples;
const { t } = useI18n();

const workflowPage = ref<InstanceType<typeof WorkflowCrudPage> | null>(null);

let unregisterTourAction: (() => void) | null = null;
onMounted(() => {
  unregisterTourAction = registerTourAction("samples-open-detail", () => {
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
    panel-id="samples"
    :title="t('nav.samples')"
    :search-placeholder="t('directionWizard.searchSamples')"
    tour-scope="samples"
  />
</template>
