<script setup lang="ts">
import { computed } from "vue";
import { CalendarDate } from "@internationalized/date";
import {
  DATE_RANGE_PRESETS,
  isDateRangePresetSelected,
  selectDateRangePreset,
  type DateRangePreset,
  type DateRangeValue,
} from "@/shared/utils/date-range";

const model = defineModel<DateRangeValue>({ required: true });

const pad = (value: number) => String(value).padStart(2, "0");
const presetCurrentDate = computed(() => new Date());

const parseDate = (value: string | null | undefined) => {
  if (!value) {
    return undefined;
  }

  const [year, month, day] = value.slice(0, 10).split("-").map(Number);
  if (!year || !month || !day) {
    return undefined;
  }

  return new CalendarDate(year, month, day);
};

const formatDate = (value: CalendarDate | undefined) =>
  value ? `${value.year}-${pad(value.month)}-${pad(value.day)}` : null;

const calendarRange = computed({
  get: () => ({
    start: parseDate(model.value?.[0]),
    end: parseDate(model.value?.[1]),
  }),
  set: (value: { start: CalendarDate | undefined; end: CalendarDate | undefined }) => {
    model.value = [formatDate(value.start), formatDate(value.end)];
  },
});

const hasValue = computed(() => Boolean(model.value?.[0] || model.value?.[1]));

const displayValue = computed(() => {
  const [start, end] = model.value ?? [null, null];
  if (start && end) {
    return `${start} - ${end}`;
  }
  return start || end || "Выберите период";
});

const clear = () => {
  model.value = [null, null];
};

const selectPreset = (preset: DateRangePreset) => {
  model.value = selectDateRangePreset(preset, presetCurrentDate.value);
};

const isPresetSelected = (preset: DateRangePreset) =>
  isDateRangePresetSelected(model.value ?? [null, null], preset, presetCurrentDate.value);
</script>

<template>
  <UFieldGroup>
    <UPopover :content="{ align: 'start' }">
      <UButton
        color="neutral"
        variant="outline"
        icon="i-lucide-calendar"
        class="w-full justify-start"
      >
        <span class="truncate">{{ displayValue }}</span>
      </UButton>

      <template #content>
        <div class="flex flex-col sm:flex-row sm:divide-x divide-default">
          <div class="flex sm:w-52 sm:flex-col sm:justify-center overflow-x-auto sm:overflow-visible">
            <UButton
              v-for="preset in DATE_RANGE_PRESETS"
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
            class="p-2"
            :number-of-months="2"
            range
          />
        </div>
      </template>
    </UPopover>

    <UTooltip text="Очистить период">
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
