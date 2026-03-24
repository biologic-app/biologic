<script setup lang="ts">
import { useFetch } from '@vueuse/core'
import { formatDistanceToNow } from 'date-fns'
import { useI18n } from 'vue-i18n'
import { useLocale } from '../composables/useLocale'
import { useDashboard } from '../composables/useDashboard'
import type { Notification } from '../types'

const { isNotificationsSlideoverOpen } = useDashboard()
const { t } = useI18n()
const { dateFnsLocale } = useLocale()

const { data: notifications } = useFetch('https://dashboard-template.nuxt.dev/api/notifications', { initialData: [] }).json<Notification[]>()

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
      <RouterLink
        v-for="notification in notifications"
        :key="notification.id"
        :to="`/inbox?id=${notification.id}`"
        class="px-3 py-2.5 rounded-md hover:bg-elevated/50 flex items-center gap-3 relative -mx-3 first:-mt-3 last:-mb-3"
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
      </RouterLink>
    </template>
  </USlideover>
</template>
