<script setup lang="ts">
import { computed, ref, shallowRef } from "vue";
import { sub } from "date-fns";
import type { DropdownMenuItem } from "@nuxt/ui";
import { useI18n } from "vue-i18n";
import { useDashboardShell } from "@/shared/composables/useDashboardShell";
import TourMenu from "@/shared/ui/TourMenu.vue";
import HomeChart from "@/modules/dashboard/components/HomeChart.vue";
import HomeDateRangePicker from "@/modules/dashboard/components/HomeDateRangePicker.vue";
import HomePeriodSelect from "@/modules/dashboard/components/HomePeriodSelect.vue";
import HomeStats from "@/modules/dashboard/components/HomeStats.vue";
import type { Period, Range } from "@/modules/dashboard/types";
import { useWorkflowRole } from "@/modules/workflows/useWorkflowRole";

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
const { selectedRole } = useWorkflowRole();
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

          <TourMenu scope="dashboard" />
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
      <section class="mb-6 rounded-lg border border-default bg-elevated/40 p-4 sm:p-5">
        <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <UBadge :label="selectedRole.shortName" color="primary" variant="solid" />
              <UBadge :label="selectedRole.entryPoint" color="neutral" variant="outline" />
            </div>
            <h2 class="mt-3 text-xl font-semibold text-highlighted">
              {{ selectedRole.title }}
            </h2>
            <p class="mt-1 max-w-3xl text-sm leading-6 text-muted">
              {{ selectedRole.subtitle }}
            </p>
          </div>

          <div class="flex shrink-0 flex-wrap gap-2">
            <UButton
              v-for="action in selectedRole.actions"
              :key="action.label"
              :to="action.route"
              :icon="action.icon"
              :label="action.label"
              :color="action.primary ? 'primary' : 'neutral'"
              :variant="action.primary ? 'solid' : 'outline'"
            />
          </div>
        </div>
      </section>

      <UPageGrid class="mb-6 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <UPageCard
          v-for="metric in selectedRole.metrics"
          :key="metric.label"
          :icon="metric.icon"
          :title="metric.label"
          variant="subtle"
          :ui="{
            container: 'gap-y-1.5',
            leading: 'rounded-md bg-elevated p-2 ring ring-default',
            title: 'text-xs font-normal uppercase text-muted',
          }"
        >
          <div class="flex items-center justify-between gap-3">
            <span class="text-2xl font-semibold text-highlighted">
              {{ metric.value }}
            </span>
            <UBadge :color="metric.tone" variant="subtle" label="роль" />
          </div>
        </UPageCard>
      </UPageGrid>

      <section class="mb-6 grid gap-3 xl:grid-cols-3">
        <div
          v-for="queue in selectedRole.queues"
          :key="queue.title"
          class="rounded-lg border border-default bg-default p-4"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="flex min-w-0 items-start gap-3">
              <div class="rounded-md bg-elevated p-2 ring ring-default">
                <UIcon :name="queue.icon" class="size-4 text-muted" />
              </div>
              <div class="min-w-0">
                <p class="truncate text-sm font-semibold text-highlighted">
                  {{ queue.title }}
                </p>
                <p class="mt-1 text-xs leading-5 text-muted">
                  {{ queue.description }}
                </p>
              </div>
            </div>
            <UBadge :color="queue.tone" :label="String(queue.count)" variant="subtle" />
          </div>

          <div class="mt-3 flex items-center justify-between gap-2">
            <UBadge :label="queue.status" color="neutral" variant="outline" />
            <UButton
              :to="queue.route"
              icon="i-lucide-arrow-up-right"
              label="Открыть"
              color="neutral"
              variant="ghost"
              size="sm"
            />
          </div>
        </div>
      </section>

      <HomeStats data-tour="dashboard-stats" :period="period" :range="range" />
      <HomeChart data-tour="dashboard-chart" :period="period" :range="range" />
    </template>
  </UDashboardPanel>
</template>
