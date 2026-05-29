<script setup lang="ts">
import { computed } from 'vue'
import { formatDistanceToNow } from 'date-fns'
import { useI18n } from 'vue-i18n'
import { useDashboardShell } from '@/shared/composables/useDashboardShell'
import { useLocale } from '@/shared/composables/useLocale'
import { useSystemNotifications } from '@/shared/composables/useSystemNotifications'
import type { Notification } from '@/shared/types'

const { isNotificationsSlideoverOpen } = useDashboardShell()
const { t } = useI18n()
const { dateFnsLocale } = useLocale()
const { unreadNotifications: unreadSystemNotifications } = useSystemNotifications()

const unreadNotifications = computed<Notification[]>(() =>
  unreadSystemNotifications.value
)

function formatNotificationTime(date: string) {
  return formatDistanceToNow(new Date(date), {
    addSuffix: true,
    locale: dateFnsLocale.value
  })
}
</script>

<template>
  <USlideover
    v-model:open="isNotificationsSlideoverOpen"
    :title="t('notifications.title')"
  >
    <template #body>
      <div v-if="!unreadNotifications.length" class="flex min-h-32 items-center justify-center text-sm text-muted">
        {{ t('notifications.noUnread') }}
      </div>

      <article
        v-for="notification in unreadNotifications"
        :key="notification.id"
        class="px-3 py-2.5 rounded-md flex items-center gap-3 relative -mx-3 first:-mt-3 last:-mb-3"
      >
        <UChip
          color="error"
          :show="!!notification.unread"
          inset
        >
          <UAvatar
            v-bind="notification.sender.avatar"
            :alt="notification.sender.name"
            size="md"
          />
        </UChip>

        <div class="text-sm flex-1">
          <p class="flex items-center justify-between">
            <span class="text-highlighted font-medium">{{ notification.sender.name }}</span>

            <time
              :datetime="notification.date"
              class="text-muted text-xs"
              v-text="formatNotificationTime(notification.date)"
            />
          </p>

          <p class="text-dimmed">
            {{ notification.body }}
          </p>
        </div>
      </article>
    </template>
  </USlideover>
</template>
