import { onMounted, ref, shallowRef } from 'vue'
import { apiReadListRequest } from '@/shared/api/client.api'
import type { Notification } from '@/shared/types'

const notifications = shallowRef<Notification[]>([])
const unreadNotifications = shallowRef<Notification[]>([])
const isFetching = ref(false)
let initialized = false

const loadNotifications = async () => {
  isFetching.value = true
  try {
    const response = await apiReadListRequest<Record<string, unknown>>('/alerts', {
      method: 'GET',
      params: { limit: 100 }
    })

    notifications.value = response.items.map<Notification>((item, index) => ({
      id: Number(item.id) || index + 1,
      unread: item.is_read === false || item.read_at === null || item.unread === true,
      sender: {
        id: 0,
        name: String(item.sender_name || item.actor_name || 'System'),
        email: String(item.sender_email || ''),
        status: 'subscribed',
        location: String(item.source || 'Backend')
      },
      body: String(item.message || item.body || item.text || ''),
      date: String(item.created_at || item.updated_at || item.date || new Date().toISOString())
    }))
    unreadNotifications.value = notifications.value.filter((notification) => notification.unread)
  } finally {
    isFetching.value = false
  }
}

export function useSystemNotifications() {
  onMounted(() => {
    if (!initialized) {
      initialized = true
      loadNotifications()
    }
  })

  return {
    notifications,
    unreadNotifications,
    isFetching,
    loadNotifications
  }
}
