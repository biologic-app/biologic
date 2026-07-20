<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import WorkflowCrudPage from "@/shared/ui/WorkflowCrudPage.vue";
import ReleasedSamplesByDirectionModal from "@/shared/ui/ReleasedSamplesByDirectionModal.vue";
import { usePermission } from "@/shared/composables/usePermission";
import { crudModules } from "@/shared/config/crud-modules";
import { registerTourAction } from "@/shared/tour/tour.actions";

const { can } = usePermission();

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

// Модалка «Выпущенные образцы по направлениям» — открывается со страницы
// образцов; из неё регистратор формирует протоколы по завершённым образцам.
const releasedOpen = ref(false);
const canViewReleased = computed(() => can("protocols", "create") || can("samples", "view"));
</script>

<template>
  <WorkflowCrudPage
    ref="workflowPage"
    :config="selectedConfig"
    panel-id="samples"
    :title="t('nav.samples')"
    :search-placeholder="t('directionWizard.searchSamples')"
    tour-scope="samples"
  >
    <template #navbar-right>
      <UButton
        v-if="canViewReleased"
        :label="t('directionWizard.releasedSamples')"
        icon="i-lucide-package-check"
        color="neutral"
        variant="subtle"
        data-testid="open-released-samples"
        data-telemetry="samples-open-released-samples"
        @click="releasedOpen = true"
      />
      <ReleasedSamplesByDirectionModal v-model:open="releasedOpen" />
    </template>
  </WorkflowCrudPage>
</template>
