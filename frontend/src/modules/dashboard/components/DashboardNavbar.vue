<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useDashboardShell } from '@/shared/composables/useDashboardShell'
import { useSystemNotifications } from '@/shared/composables/useSystemNotifications'
import TourMenu from '@/shared/ui/TourMenu.vue'

defineProps<{
  title: string
  tourScope?: string
}>()

const { isNotificationsSlideoverOpen } = useDashboardShell()
const { unreadNotifications } = useSystemNotifications()
const { t } = useI18n()
</script>

<template>
  <UDashboardNavbar
    :title="title"
    :ui="{ right: 'gap-3' }"
  >
    <template #leading>
      <UDashboardSidebarCollapse />
    </template>

    <template #right>
      <slot name="right-leading" />

      <UTooltip
        :text="t('dashboard.notifications')"
        :kbds="['N']"
      >
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
            <UIcon
              name="i-lucide-bell"
              class="size-5 shrink-0"
            />
          </UChip>
        </UButton>
      </UTooltip>

      <TourMenu
        v-if="tourScope"
        :scope="tourScope"
      />
    </template>
  </UDashboardNavbar>
</template>
