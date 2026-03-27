<script setup lang="ts">
import { computed, ref, shallowRef } from "vue";
import { sub } from "date-fns";
import type { DropdownMenuItem } from "@nuxt/ui";
import { useI18n } from "vue-i18n";
import { useDashboardShell } from "@/shared/composables/useDashboardShell";
import TourMenu from "@/shared/components/TourMenu.vue";
import HomeChart from "@/modules/dashboard/components/HomeChart.vue";
import HomeDateRangePicker from "@/modules/dashboard/components/HomeDateRangePicker.vue";
import HomePeriodSelect from "@/modules/dashboard/components/HomePeriodSelect.vue";
import HomeStats from "@/modules/dashboard/components/HomeStats.vue";
import type { Period, Range } from "@/modules/dashboard/types";

const { isNotificationsSlideoverOpen } = useDashboardShell();
const { t } = useI18n();

const items = computed<DropdownMenuItem[][]>(() => [
  [
    {
      label: t("dashboard.newMail"),
      icon: "i-lucide-send",
      to: "/inbox",
    },
    {
      label: t("dashboard.newCustomer"),
      icon: "i-lucide-user-plus",
      to: "/customers",
    },
  ],
]);

const range = shallowRef<Range>({
  start: sub(new Date(), { days: 14 }),
  end: new Date(),
});
const period = ref<Period>("daily");
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
              <UChip color="error" inset>
                <UIcon name="i-lucide-bell" class="size-5 shrink-0" />
              </UChip>
            </UButton>
          </UTooltip>
          <UDropdownMenu :items="items">
            <UTooltip :text="t('dashboard.quickActions')">
              <UButton
                data-tour="dashboard-quick-actions"
                icon="i-lucide-plus"
                size="md"
                variant="subtle"
                class="rounded-full"
              />
            </UTooltip>
          </UDropdownMenu>
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
      <HomeStats data-tour="dashboard-stats" :period="period" :range="range" />
      <HomeChart data-tour="dashboard-chart" :period="period" :range="range" />
    </template>
  </UDashboardPanel>
</template>
