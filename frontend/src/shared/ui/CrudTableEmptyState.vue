<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";

const { t } = useI18n();

const props = withDefaults(
  defineProps<{
    title?: string;
    description?: string;
    filtered?: boolean;
    error?: boolean;
    errorDescription?: string;
  }>(),
  {
    filtered: false,
    error: false,
  },
);

const resolvedTitle = computed(() => props.title ?? t("crud.noData"));
const resolvedDescription = computed(() => props.description ?? t("crud.changeFiltersOrCreateRecord"));
const resolvedErrorDescription = computed(() => props.errorDescription ?? t("crud.tryRefreshOrRetryLater"));

const emit = defineEmits<{
  (e: "clearFilters"): void;
  (e: "retry"): void;
}>();
</script>

<template>
  <div class="flex min-h-[min(34rem,calc(100vh-18rem))] w-full items-center justify-center px-8 py-16">
    <UEmpty
      v-if="error"
      variant="naked"
      size="xl"
      icon="i-lucide-cloud-off"
      :title="t('crud.failedToLoadDataTitle')"
      :description="resolvedErrorDescription"
      class="max-w-xl"
    >
      <template #actions>
        <UButton
          color="neutral"
          variant="outline"
          size="sm"
          icon="i-lucide-refresh-cw"
          :label="t('crud.retry')"
          @click="emit('retry')"
        />
      </template>
    </UEmpty>

    <UEmpty
      v-else
      variant="naked"
      size="xl"
      :icon="filtered ? 'i-lucide-search-x' : 'i-lucide-inbox'"
      :title="resolvedTitle"
      :description="resolvedDescription"
      class="max-w-xl"
    >
      <template
        v-if="filtered"
        #actions
      >
        <UButton
          color="neutral"
          variant="outline"
          size="sm"
          icon="i-lucide-filter-x"
          :label="t('crud.resetFiltersTooltip')"
          @click="emit('clearFilters')"
        />
      </template>
    </UEmpty>
  </div>
</template>
