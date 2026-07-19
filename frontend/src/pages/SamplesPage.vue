<script setup lang="ts">
import { computed, ref } from "vue";
import WorkflowCrudPage from "@/shared/ui/WorkflowCrudPage.vue";
import ReleasedSamplesByDirectionModal from "@/shared/ui/ReleasedSamplesByDirectionModal.vue";
import { usePermission } from "@/shared/composables/usePermission";
import { crudModules } from "@/shared/config/crud-modules";

const { can } = usePermission();

const selectedConfig = crudModules.samples;

// Модалка «Выпущенные образцы по направлениям» — открывается со страницы
// образцов; из неё регистратор формирует протоколы по завершённым образцам.
const releasedOpen = ref(false);
const canViewReleased = computed(() => can("protocols", "create") || can("samples", "view"));
</script>

<template>
  <WorkflowCrudPage
    :config="selectedConfig"
    panel-id="samples"
    title="Образцы"
    search-placeholder="Поиск по образцам"
  >
    <template #navbar-right>
      <UButton
        v-if="canViewReleased"
        label="Выпущенные образцы"
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
