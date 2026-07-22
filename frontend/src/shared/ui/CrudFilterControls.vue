<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";

const { t } = useI18n();

const props = withDefaults(
  defineProps<{
    activeCount?: number;
    label?: string;
    clearTooltip?: string;
  }>(),
  {
    activeCount: 0,
  },
);

const resolvedLabel = computed(() => props.label ?? t("common.filter"));
const resolvedClearTooltip = computed(() => props.clearTooltip ?? t("crud.resetFiltersTooltip"));

const emit = defineEmits<{
  (event: "open"): void;
  (event: "clear"): void;
}>();
</script>

<template>
  <UFieldGroup>
    <UButton
      data-tour="crud-filter"
      :label="resolvedLabel"
      color="neutral"
      variant="subtle"
      icon="i-lucide-filter"
      @click="emit('open')"
    >
      <template v-if="activeCount > 0" #trailing>
        <UKbd>{{ activeCount }}</UKbd>
      </template>
    </UButton>

    <UTooltip :text="resolvedClearTooltip">
      <UButton
        color="neutral"
        variant="subtle"
        size="sm"
        class="px-2"
        icon="i-lucide-filter-x"
        @click="emit('clear')"
      />
    </UTooltip>
  </UFieldGroup>
</template>
