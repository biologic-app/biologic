<script setup lang="ts">
import NotificationsBellButton from '@/shared/ui/NotificationsBellButton.vue'
import TourMenu from '@/shared/ui/TourMenu.vue'
import CurrentBranchBadge from '@/shared/ui/CurrentBranchBadge.vue'

defineProps<{
  title: string
  tourScope?: string
}>()
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

      <CurrentBranchBadge />

      <NotificationsBellButton data-tour="dashboard-notifications" />

      <TourMenu
        v-if="tourScope"
        :scope="tourScope"
      />
    </template>
  </UDashboardNavbar>
</template>
