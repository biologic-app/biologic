<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { useDashboardShell } from "@/shared/composables/useDashboardShell";
import { useSystemNotifications } from "@/shared/composables/useSystemNotifications";

withDefaults(
  defineProps<{
    dataTour?: string;
  }>(),
  {
    dataTour: undefined,
  },
);

const { isNotificationsSlideoverOpen } = useDashboardShell();
const { unreadNotifications } = useSystemNotifications();
const { t } = useI18n();
</script>

<template>
  <UTooltip :text="t('dashboard.notifications')" :kbds="['N']">
    <UButton
      :data-tour="dataTour"
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
</template>
