<script setup lang="ts">
import type { CalendarDate } from "@internationalized/date";

export type DateRangeCalendarValue = {
  start: CalendarDate | undefined;
  end: CalendarDate | undefined;
};

export type DateRangePresetOption = {
  label: string;
  selected: boolean;
};

withDefaults(
  defineProps<{
    presets: DateRangePresetOption[];
    maxValue?: CalendarDate;
    numberOfMonths?: number;
    weekNumbers?: boolean;
  }>(),
  {
    maxValue: undefined,
    numberOfMonths: 2,
    weekNumbers: false,
  },
);

const emit = defineEmits<{
  (e: "selectPreset", index: number): void;
}>();

const model = defineModel<DateRangeCalendarValue>({ required: true });
</script>

<template>
  <UPopover :content="{ align: 'start' }" :modal="true">
    <slot name="trigger" />

    <template #content>
      <div class="flex flex-col sm:flex-row sm:divide-x divide-default">
        <div class="flex sm:w-52 sm:flex-col sm:justify-center overflow-x-auto sm:overflow-visible">
          <UButton
            v-for="(preset, index) in presets"
            :key="preset.label"
            :label="preset.label"
            color="neutral"
            variant="ghost"
            class="w-full justify-start rounded-none px-4"
            :ui="{ label: 'w-full text-left' }"
            :class="preset.selected ? 'bg-elevated' : 'hover:bg-elevated/50'"
            truncate
            @click="emit('selectPreset', index)"
          />
        </div>

        <UCalendar
          v-model="model"
          :max-value="maxValue"
          class="p-2"
          :number-of-months="numberOfMonths"
          :week-numbers="weekNumbers"
          range
        />
      </div>
    </template>
  </UPopover>
</template>
