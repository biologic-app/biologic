<script setup lang="ts">
import { ref, shallowRef, watch } from "vue";
import { sub } from "date-fns";
import { useI18n } from "vue-i18n";
import { useDashboardShell } from "@/shared/composables/useDashboardShell";
import { useSystemNotifications } from "@/shared/composables/useSystemNotifications";
import TourMenu from "@/shared/ui/TourMenu.vue";
import { loadDashboardSummary } from "@/modules/dashboard/dashboard.api";
import HomeChart from "@/modules/dashboard/components/HomeChart.vue";
import HomeDateRangePicker from "@/modules/dashboard/components/HomeDateRangePicker.vue";
import HomePeriodSelect from "@/modules/dashboard/components/HomePeriodSelect.vue";
import HomeStats from "@/modules/dashboard/components/HomeStats.vue";
import type { DashboardSummary, Period, Range } from "@/modules/dashboard/types";

const { isNotificationsSlideoverOpen } = useDashboardShell();
const { unreadNotifications } = useSystemNotifications();
const { t } = useI18n();

const range = shallowRef<Range>({
  start: sub(new Date(), { days: 14 }),
  end: new Date(),
});
const period = ref<Period>("daily");
const summary = shallowRef<DashboardSummary | null>(null);
const isLoading = ref(false);
const errorMessage = ref<string | null>(null);
let requestSerial = 0;

const resolveErrorMessage = (error: unknown) => {
  if (error instanceof Error) {
    return error.message;
  }

  if (
    typeof error === "object" &&
    error !== null &&
    "message" in error &&
    typeof error.message === "string"
  ) {
    return error.message;
  }

  return t("dashboard.error");
};

watch([range, period], async () => {
  const serial = ++requestSerial;
  isLoading.value = true;
  errorMessage.value = null;

  try {
    const nextSummary = await loadDashboardSummary(range.value, period.value);
    if (serial === requestSerial) {
      summary.value = nextSummary;
    }
  } catch (error) {
    if (serial === requestSerial) {
      errorMessage.value = resolveErrorMessage(error);
      summary.value = null;
    }
  } finally {
    if (serial === requestSerial) {
      isLoading.value = false;
    }
  }
}, { immediate: true });
</script>

<template>
  <UDashboardPanel id="home">
    <template #header>
      <UDashboardNavbar :title="t('nav.home')" :ui="{ right: 'gap-3' }">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>

        <template #right>
          <UTooltip :text="t('dashboard.notifications')" :kbds="['N']">
            <UButton
              data-tour="dashboard-notifications"
              color="neutral"
              variant="ghost"
              square
              @click="isNotificationsSlideoverOpen = true"
            >
              <UChip
                color="error"
                inset
                :text="unreadNotifications.length ? String(unreadNotifications.length) : undefined"
                :show="unreadNotifications.length > 0"
              >
                <UIcon name="i-lucide-bell" class="size-5 shrink-0" />
              </UChip>
            </UButton>
          </UTooltip>

          <TourMenu scope="dashboard" />
        </template>
      </UDashboardNavbar>

      <UDashboardToolbar>
        <template #left>
          <HomeDateRangePicker
            v-model="range"
            data-tour="dashboard-range"
            class="-ms-1"
          />

          <HomePeriodSelect
            v-model="period"
            data-tour="dashboard-period"
            :range="range"
          />
        </template>
      </UDashboardToolbar>
    </template>

    <template #body>
      <div class="space-y-6">
        <UAlert
          v-if="errorMessage"
          color="error"
          variant="subtle"
          icon="i-lucide-circle-alert"
          :title="t('dashboard.loadError')"
          :description="errorMessage"
        />

        <HomeStats
          data-tour="dashboard-stats"
          :summary="summary"
          :loading="isLoading"
        />

        <HomeChart
          data-tour="dashboard-chart"
          :summary="summary"
          :period="period"
          :loading="isLoading"
        />
      </div>
    </template>
  </UDashboardPanel>
</template>
