import { computed, onMounted, ref, shallowRef } from 'vue'
import { apiCommandRequest, apiReadListRequest, buildApiUrl } from '@/shared/api/client.api'
import { useAuth } from '@/modules/auth'
import type { Notification } from '@/shared/types'

interface BackendNotification {
  id: string
  kind: string
  title: string
  message: string
  entity_type?: string
  entity_id?: string
  source_event_type?: string
  payload?: Record<string, unknown>
  read_at: string | null
  created_at: string
  target_user_id: string | null
  target_role_key: string | null
}

const SYSTEM_ACTOR_ID = '00000000-0000-0000-0000-000000000000'

const notifications = shallowRef<Notification[]>([])
const isFetching = ref(false)
let initialized = false
let eventSource: EventSource | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null

const unreadNotifications = computed<Notification[]>(() =>
  notifications.value.filter((notification) => notification.readAt === null)
)

const readNotifications = computed<Notification[]>(() =>
  notifications.value.filter((notification) => notification.readAt !== null)
)

const upsertNotification = (notification: Notification) => {
  const existingIndex = notifications.value.findIndex((item) => item.id === notification.id)
  if (existingIndex === -1) {
    notifications.value = [notification, ...notifications.value]
    return
  }

  notifications.value = notifications.value.map((item, index) =>
    index === existingIndex ? notification : item
  )
}

const mapNotification = (item: BackendNotification): Notification => ({
  id: item.id,
  unread: item.read_at === null,
  title: item.title,
  sender: {
    id: 0,
    name: 'System',
    email: '',
    status: 'subscribed',
    location: item.entity_type || 'Backend'
  },
  body: item.message,
  date: item.created_at,
  readAt: item.read_at
})

const loadNotifications = async () => {
  isFetching.value = true
  try {
    const [unreadResponse, readResponse] = await Promise.all([
      apiReadListRequest<BackendNotification>('/alerts', {
        method: 'GET',
        params: { limit: 100, status: 'unread' }
      }),
      apiReadListRequest<BackendNotification>('/alerts', {
        method: 'GET',
        params: { limit: 100, status: 'read' }
      })
    ])

    notifications.value = [...unreadResponse.items, ...readResponse.items]
      .map(mapNotification)
      .sort((left, right) => new Date(right.date).getTime() - new Date(left.date).getTime())
  } finally {
    isFetching.value = false
  }
}

const ensureNotificationPermission = async (): Promise<void> => {
  if (!('Notification' in window) || window.Notification.permission !== 'default') {
    return
  }
  await window.Notification.requestPermission()
}

// Replaces the in-app toast with an OS notification when the tab/PWA is open
// but not focused (backgrounded, minimized, another window active) — the SSE
// connection still delivers the event, but the user wouldn't see the toast.
// False when unsupported (e.g. iOS Safari outside a home-screen install),
// permission isn't granted, or the tab is actually focused — the toast
// covers all of those cases instead.
const canShowSystemNotification = (): boolean =>
  'serviceWorker' in navigator &&
  'Notification' in window &&
  window.Notification.permission === 'granted' &&
  !(document.visibilityState === 'visible' && document.hasFocus())

const showSystemNotification = async (notification: Notification): Promise<void> => {
  const registration = await navigator.serviceWorker.ready
  await registration.showNotification(notification.title, {
    body: notification.body,
    icon: '/icon-192.png',
    tag: notification.id
  })
}

const connectNotificationStream = (showToast: (notification: Notification) => void) => {
  if (eventSource) {
    return
  }
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }

  eventSource = new EventSource(buildApiUrl('/alerts/stream'), { withCredentials: true })
  eventSource.addEventListener('notification.created', (event) => {
    const notification = mapNotification(JSON.parse(event.data) as BackendNotification)
    upsertNotification(notification)
    if (canShowSystemNotification()) {
      void showSystemNotification(notification)
    } else {
      showToast(notification)
    }
  })
  eventSource.onerror = () => {
    eventSource?.close()
    eventSource = null
    reconnectTimer = setTimeout(() => connectNotificationStream(showToast), 3000)
  }
}

export function useSystemNotifications() {
  const toast = useToast()
  const auth = useAuth()

  onMounted(() => {
    if (!initialized) {
      initialized = true
      void ensureNotificationPermission()
      loadNotifications()
      connectNotificationStream((notification) => {
        toast.add({
          title: notification.title,
          description: notification.body,
          icon: 'i-lucide-bell',
          color: 'primary'
        })
      })
    }
  })

  const markNotificationRead = async (notificationId: string) => {
    const actorId = auth.user?.id || SYSTEM_ACTOR_ID
    const response = await apiCommandRequest<BackendNotification>(`/alerts/${notificationId}/mark-read`, {
      method: 'POST',
      body: { actor_id: actorId }
    })
    upsertNotification(mapNotification(response.data))
  }

  return {
    notifications,
    unreadNotifications,
    readNotifications,
    isFetching,
    loadNotifications,
    markNotificationRead
  }
}
