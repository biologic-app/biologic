<script setup lang="ts">
import { computed, ref } from 'vue'
import { formatDistanceToNow } from 'date-fns'
import type { TabsItem } from '@nuxt/ui'
import { useI18n } from 'vue-i18n'
import { useDashboardShell } from '@/shared/composables/useDashboardShell'
import { useLocale } from '@/shared/composables/useLocale'
import { useSystemNotifications } from '@/shared/composables/useSystemNotifications'
import type { Notification } from '@/shared/types'

const { isNotificationsSlideoverOpen } = useDashboardShell()
const { t } = useI18n()
const { dateFnsLocale } = useLocale()
const {
  unreadNotifications,
  readNotifications,
  markNotificationRead
} = useSystemNotifications()

const activeTab = ref<'unread' | 'read'>('unread')

const tabItems = computed<TabsItem[]>(() => [
  {
    label: `${t('notifications.tabs.unread')} (${unreadNotifications.value.length})`,
    icon: 'i-lucide-bell',
    value: 'unread'
  },
  {
    label: `${t('notifications.tabs.read')} (${readNotifications.value.length})`,
    icon: 'i-lucide-check-check',
    value: 'read'
  }
])

const visibleNotifications = computed<Notification[]>(() =>
  activeTab.value === 'unread' ? unreadNotifications.value : readNotifications.value
)

const emptyText = computed(() =>
  activeTab.value === 'unread' ? t('notifications.noUnread') : t('notifications.noRead')
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
      <div class="space-y-4">
        <UTabs
          v-model="activeTab"
          :items="tabItems"
          variant="link"
          :content="false"
        />

        <div v-if="!visibleNotifications.length" class="flex min-h-32 items-center justify-center text-sm text-muted">
          {{ emptyText }}
        </div>

        <article
          v-for="notification in visibleNotifications"
          :key="notification.id"
          class="rounded-md px-3 py-2.5 flex items-start gap-3 relative -mx-3"
        >
          <UChip
            color="error"
            :show="notification.readAt === null"
            inset
          >
            <UAvatar
              v-bind="notification.sender.avatar"
              :alt="notification.sender.name"
              icon="i-lucide-bell"
              size="md"
            />
          </UChip>

          <div class="text-sm min-w-0 flex-1">
            <p class="flex items-center justify-between gap-3">
              <span class="text-highlighted font-medium truncate">{{ notification.title }}</span>

              <time
                :datetime="notification.date"
                class="text-muted text-xs shrink-0"
                v-text="formatNotificationTime(notification.date)"
              />
            </p>

            <p class="text-dimmed mt-1">
              {{ notification.body }}
            </p>

            <div v-if="notification.readAt === null" class="mt-2">
              <UButton
                size="xs"
                variant="soft"
                color="neutral"
                icon="i-lucide-check"
                @click="markNotificationRead(notification.id)"
              >
                {{ t('notifications.markRead') }}
              </UButton>
            </div>
          </div>
        </article>
      </div>
    </template>
  </USlideover>
</template>
