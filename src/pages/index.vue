<script setup lang="ts">
import { computed, ref, shallowRef } from 'vue'
import { sub } from 'date-fns'
import type { DropdownMenuItem } from '@nuxt/ui'
import { useI18n } from 'vue-i18n'
import { useDashboard } from '../composables/useDashboard'
import type { Period, Range } from '../types'

const { isNotificationsSlideoverOpen } = useDashboard()
const { t } = useI18n()

const items = computed<DropdownMenuItem[][]>(() => [[{
  label: t('dashboard.newMail'),
  icon: 'i-lucide-send',
  to: '/inbox'
}, {
  label: t('dashboard.newCustomer'),
  icon: 'i-lucide-user-plus',
  to: '/customers'
}]])

const range = shallowRef<Range>({
  start: sub(new Date(), { days: 14 }),
  end: new Date()
})
const period = ref<Period>('daily')
</script>

<template>
  <UDashboardPanel id="home">
    <template #header>
      <UDashboardNavbar :title="t('nav.home')" :ui="{ right: 'gap-3' }">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>

        <template #right>
          <UTooltip :text="t('dashboard.notifications')" :shortcuts="['N']">
            <UButton
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
              <UButton icon="i-lucide-plus" size="md" class="rounded-full" />
            </UTooltip>
          </UDropdownMenu>
        </template>
      </UDashboardNavbar>

      <UDashboardToolbar>
        <template #left>
          <HomeDateRangePicker v-model="range" class="-ms-1" />

          <HomePeriodSelect v-model="period" :range="range" />
        </template>
      </UDashboardToolbar>
    </template>

    <template #body>
      <HomeStats :period="period" :range="range" />
      <HomeChart :period="period" :range="range" />
    </template>
  </UDashboardPanel>
</template>
