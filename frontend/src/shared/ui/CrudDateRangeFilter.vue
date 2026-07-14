<script setup lang="ts">
import { computed } from "vue";
import { CalendarDate, getLocalTimeZone, parseDate as parseCalendarDate, today } from "@internationalized/date";
import { useI18n } from "vue-i18n";
import { useLocale } from "@/shared/composables/useLocale";
import DateRangeCalendarPopover from "@/shared/ui/DateRangeCalendarPopover.vue";
import {
  DATE_RANGE_PRESETS,
  isDateRangePresetSelected,
  selectDateRangePreset,
  type DateRangePreset,
  type DateRangeValue,
} from "@/shared/utils/date-range";

const model = defineModel<DateRangeValue>({ required: true });
const { t } = useI18n();
const { intlLocale } = useLocale();
const presetCurrentDate = computed(() => new Date());
const rangeLabelKeys = [
  "last7Days",
  "last14Days",
  "last30Days",
  "last3Months",
  "last6Months",
  "lastYear",
] as const;

const ranges = computed<DateRangePreset[]>(() =>
  DATE_RANGE_PRESETS.map((preset, index) => ({
    ...preset,
    label: t(`dashboard.ranges.${rangeLabelKeys[index] ?? "last7Days"}`),
  })),
);

const toCalendarDate = (value: string | null | undefined) => {
  if (!value) {
    return undefined;
  }

  try {
    return parseCalendarDate(value.slice(0, 10));
  } catch {
    return undefined;
  }
};

const formatDate = (value: CalendarDate | undefined) =>
  value ? value.toString() : null;

const calendarRange = computed({
  get: () => ({
    start: toCalendarDate(model.value?.[0]),
    end: toCalendarDate(model.value?.[1]),
  }),
  set: (value: { start: CalendarDate | undefined; end: CalendarDate | undefined }) => {
    model.value = [formatDate(value.start), formatDate(value.end)];
  },
});

const hasValue = computed(() => Boolean(model.value?.[0] || model.value?.[1]));

// Disallow picking future dates in date-range filters.
const maxDate = today(getLocalTimeZone());

const displayValue = computed(() => {
  const [start, end] = model.value ?? [null, null];
  const startDate = toCalendarDate(start);
  const endDate = toCalendarDate(end);

  if (startDate && endDate) {
    return `${formatDisplayDate(startDate)} - ${formatDisplayDate(endDate)}`;
  }
  if (startDate) {
    return formatDisplayDate(startDate);
  }
  if (endDate) {
    return formatDisplayDate(endDate);
  }
  return t("common.pickDateRange");
});

const clear = () => {
  model.value = [null, null];
};

const selectPresetByIndex = (index: number) => {
  const preset = ranges.value[index];
  if (preset) {
    model.value = selectDateRangePreset(preset, presetCurrentDate.value);
  }
};

const isPresetSelected = (preset: DateRangePreset) =>
  isDateRangePresetSelected(model.value ?? [null, null], preset, presetCurrentDate.value);

const presetOptions = computed(() =>
  ranges.value.map((preset) => ({
    label: preset.label,
    selected: isPresetSelected(preset),
  })),
);

const formatDisplayDate = (value: CalendarDate) =>
  new Intl.DateTimeFormat(intlLocale.value, { dateStyle: "medium" }).format(
    value.toDate(getLocalTimeZone()),
  );
</script>

<template>
  <UFieldGroup>
    <DateRangeCalendarPopover
      v-model="calendarRange"
      :presets="presetOptions"
      :max-value="maxDate"
      :number-of-months="2"
      @select-preset="selectPresetByIndex"
    >
      <template #trigger>
        <UButton
          color="neutral"
          variant="outline"
          icon="i-lucide-calendar"
          block
          class="justify-start data-[state=open]:bg-elevated group"
        >
          <span class="truncate">{{ displayValue }}</span>
        </UButton>
      </template>
    </DateRangeCalendarPopover>

    <UTooltip :text="t('common.clear')">
      <UButton
        color="neutral"
        variant="outline"
        icon="i-lucide-x"
        :disabled="!hasValue"
        @click="clear"
      />
    </UTooltip>
  </UFieldGroup>
</template>
