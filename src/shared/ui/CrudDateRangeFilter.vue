<script setup lang="ts">
import { computed } from "vue";
import { CalendarDate, getLocalTimeZone, parseDate, today } from "@internationalized/date";
import { useI18n } from "vue-i18n";
import { useLocale } from "@/shared/composables/useLocale";

type DateRangeValue = (string | null)[];

const selected = defineModel<DateRangeValue>({ required: true });
const { t } = useI18n();
const { intlLocale } = useLocale();

const ranges = computed(() => [
  { label: t("dashboard.ranges.last7Days"), days: 7 },
  { label: t("dashboard.ranges.last14Days"), days: 14 },
  { label: t("dashboard.ranges.last30Days"), days: 30 },
  { label: t("dashboard.ranges.last3Months"), months: 3 },
  { label: t("dashboard.ranges.last6Months"), months: 6 },
  { label: t("dashboard.ranges.lastYear"), years: 1 },
]);

const toCalendarDate = (value: string | null | undefined): CalendarDate | undefined => {
  if (!value) return undefined;
  try {
    return parseDate(value.slice(0, 10));
  } catch {
    return undefined;
  }
};

const startDate = computed(() => toCalendarDate(selected.value?.[0]));
const endDate = computed(() => toCalendarDate(selected.value?.[1]));

const calendarRange = computed({
  get: () => ({ start: startDate.value, end: endDate.value }),
  set: (newValue: { start: CalendarDate | undefined; end: CalendarDate | undefined }) => {
    selected.value = [
      newValue.start ? newValue.start.toString() : null,
      newValue.end ? newValue.end.toString() : null,
    ];
  },
});

type Preset = { days?: number; months?: number; years?: number };

const presetStart = (range: Preset): CalendarDate => {
  let start = today(getLocalTimeZone());
  if (range.days) start = start.subtract({ days: range.days });
  else if (range.months) start = start.subtract({ months: range.months });
  else if (range.years) start = start.subtract({ years: range.years });
  return start;
};

const isRangeSelected = (range: Preset) => {
  if (!startDate.value || !endDate.value) return false;
  const end = today(getLocalTimeZone());
  return startDate.value.compare(presetStart(range)) === 0 && endDate.value.compare(end) === 0;
};

const selectRange = (range: Preset) => {
  selected.value = [presetStart(range).toString(), today(getLocalTimeZone()).toString()];
};

const clear = () => {
  selected.value = [null, null];
};

const formatDisplayDate = (value: CalendarDate) =>
  new Intl.DateTimeFormat(intlLocale.value, { dateStyle: "medium" }).format(
    value.toDate(getLocalTimeZone()),
  );
</script>

<template>
  <UPopover :content="{ align: 'start' }" :modal="true">
    <UButton
      color="neutral"
      variant="outline"
      icon="i-lucide-calendar"
      block
      class="justify-start data-[state=open]:bg-elevated group"
    >
      <span class="truncate">
        <template v-if="startDate">
          <template v-if="endDate">
            {{ formatDisplayDate(startDate) }} - {{ formatDisplayDate(endDate) }}
          </template>
          <template v-else>
            {{ formatDisplayDate(startDate) }}
          </template>
        </template>
        <template v-else>
          {{ t("common.pickDateRange") }}
        </template>
      </span>

      <template #trailing>
        <UIcon
          name="i-lucide-chevron-down"
          class="shrink-0 text-dimmed size-5 group-data-[state=open]:rotate-180 transition-transform duration-200"
        />
      </template>
    </UButton>

    <template #content>
      <div class="flex items-stretch sm:divide-x divide-default">
        <div class="hidden sm:flex flex-col justify-center">
          <UButton
            v-for="(range, index) in ranges"
            :key="index"
            :label="range.label"
            color="neutral"
            variant="ghost"
            class="rounded-none px-4"
            :class="[isRangeSelected(range) ? 'bg-elevated' : 'hover:bg-elevated/50']"
            truncate
            @click="selectRange(range)"
          />
          <UButton
            :label="t('common.clear')"
            color="neutral"
            variant="ghost"
            icon="i-lucide-x"
            class="rounded-none px-4 hover:bg-elevated/50"
            truncate
            @click="clear"
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
</template>
