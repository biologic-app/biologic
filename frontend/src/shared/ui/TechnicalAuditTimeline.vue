<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import { formatDateTime } from "@/shared/utils/format";
import {
  getLastStepperIndex,
  timelineEventsToStepperItems,
  timelineStepperUi,
} from "@/shared/ui/timeline-stepper";

export interface TechnicalAuditEvent {
  id: string;
  label: string;
  description: string;
  actor: string;
  date?: string | null;
}

const props = defineProps<{
  events: TechnicalAuditEvent[];
}>();

const stepperItems = computed(() => timelineEventsToStepperItems(props.events, "i-lucide-history"));
const activeStepIndex = computed(() => getLastStepperIndex(stepperItems.value));
const { t } = useI18n();
</script>

<template>
  <section class="max-w-3xl">
    <div class="mb-3 flex items-center justify-between gap-3">
      <h3 class="text-sm font-semibold text-highlighted">
        {{ t('entityDetail.technicalAuditTab') }}
      </h3>
      <UBadge color="neutral" variant="outline" :label="t('entityDetail.timeline.eventsCount', { n: events.length }, events.length)" />
    </div>

    <UStepper
      v-if="stepperItems.length"
      orientation="vertical"
      :items="stepperItems"
      :model-value="activeStepIndex"
      disabled
      class="w-full"
      :ui="timelineStepperUi"
    >
      <template #description="{ item: stepperItem }">
        <div class="space-y-1">
          <p class="whitespace-pre-line break-words text-xs leading-5 text-muted">
            {{ stepperItem.description }}
          </p>
          <div class="flex flex-wrap items-center gap-2">
            <UBadge
              v-if="stepperItem.actor"
              color="neutral"
              variant="outline"
              size="sm"
              :label="stepperItem.actor"
            />
            <p class="font-mono text-xs text-muted">
              {{ stepperItem.date ? formatDateTime(stepperItem.date) : t('entityDetail.timeline.noDate') }}
            </p>
          </div>
        </div>
      </template>
    </UStepper>

    <p v-else class="text-sm text-muted">
      {{ t('technicalAudit.noEvents') }}
    </p>
  </section>
</template>
