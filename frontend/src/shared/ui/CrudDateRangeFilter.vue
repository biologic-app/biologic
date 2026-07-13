<script setup lang="ts">
import { computed } from "vue";
import { CalendarDate, getLocalTimeZone, parseDate as parseCalendarDate, today } from "@internationalized/date";
import { useI18n } from "vue-i18n";
import { useLocale } from "@/shared/composables/useLocale";
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

const selectPreset = (preset: DateRangePreset) => {
  model.value = selectDateRangePreset(preset, presetCurrentDate.value);
};

const isPresetSelected = (preset: DateRangePreset) =>
  isDateRangePresetSelected(model.value ?? [null, null], preset, presetCurrentDate.value);

const formatDisplayDate = (value: CalendarDate) =>
  new Intl.DateTimeFormat(intlLocale.value, { dateStyle: "medium" }).format(
    value.toDate(getLocalTimeZone()),
  );
</script>

<template>
  <UFieldGroup>
    <UPopover :content="{ align: 'start' }" :modal="true">
      <UButton
        color="neutral"
        variant="outline"
        icon="i-lucide-calendar"
        block
        class="justify-start data-[state=open]:bg-elevated group"
      >
        <span class="truncate">{{ displayValue }}</span>
      </UButton>

      <template #content>
        <div class="flex flex-col sm:flex-row sm:divide-x divide-default">
          <div class="flex sm:w-52 sm:flex-col sm:justify-center overflow-x-auto sm:overflow-visible">
            <UButton
              v-for="preset in ranges"
              :key="preset.label"
              :label="preset.label"
              color="neutral"
              variant="ghost"
              class="w-full justify-start rounded-none px-4"
              :ui="{ label: 'w-full text-left' }"
              :class="[
                isPresetSelected(preset)
                  ? 'bg-elevated'
                  : 'hover:bg-elevated/50',
              ]"
              truncate
              @click="selectPreset(preset)"
            />
          </div>

          <UCalendar
            v-model="calendarRange"
            :max-value="maxDate"
            class="p-2"
            :number-of-months="2"
            range
          />
        </div>
      </template>
    </UPopover>

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
