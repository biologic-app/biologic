import { computed, onMounted, ref, shallowRef } from 'vue'
import { apiCommandRequest, apiReadListRequest, buildApiUrl } from '@/shared/api/client.api'
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

// Prompts for OS-notification permission on every page load (called from
// onMounted, whose one-shot guard resets on a full reload). The native dialog
// can only be raised while permission is still 'default' — once the user has
// granted it there is nothing to ask, and once 'denied' the browser suppresses
// the dialog for good (only a manual reset in site settings re-enables it), so
// re-requesting in those states is a no-op by design, not a missed prompt.
const ensureNotificationPermission = async (): Promise<void> => {
  if (!('Notification' in window) || window.Notification.permission !== 'default') {
    return
  }
  await window.Notification.requestPermission()
}

// OS notifications take priority whenever the browser supports them and the
// user has granted permission — regardless of tab focus. The in-app toast is
// only a fallback for when an OS notification can't be shown (unsupported, or
// permission still 'default'/'denied').
const canShowSystemNotification = (): boolean =>
  'Notification' in window && window.Notification.permission === 'granted'

// Shows an OS notification for a live tab. Returns false (so the caller falls
// back to the toast) if delivery isn't possible, instead of silently losing it.
// A registered service worker is preferred (required on Android Chrome, and it
// outlives the tab), but in dev no worker is registered — navigator.serviceWorker
// .ready would then hang forever, so use getRegistration() (resolves at once)
// and fall back to the plain Notification constructor, which a live tab can use
// without any worker.
const showSystemNotification = async (notification: Notification): Promise<boolean> => {
  const options: NotificationOptions = {
    body: notification.body,
    icon: '/icon-192.png',
    tag: notification.id
  }
  try {
    const registration =
      'serviceWorker' in navigator ? await navigator.serviceWorker.getRegistration() : undefined
    if (registration) {
      await registration.showNotification(notification.title, options)
      return true
    }
    new window.Notification(notification.title, options)
    return true
  } catch {
    return false
  }
}

// Prefers an OS notification when the tab is open but unfocused, and always
// falls back to the in-app toast when one can't be shown — so an arriving
// notification is never silently dropped.
const deliverNotification = async (
  notification: Notification,
  showToast: (notification: Notification) => void
): Promise<void> => {
  if (canShowSystemNotification() && (await showSystemNotification(notification))) {
    return
  }
  showToast(notification)
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
    void deliverNotification(notification, showToast)
  })
  eventSource.onerror = () => {
    eventSource?.close()
    eventSource = null
    reconnectTimer = setTimeout(() => connectNotificationStream(showToast), 3000)
  }
}

export function useSystemNotifications() {
  const toast = useToast()

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
    const response = await apiCommandRequest<BackendNotification>(`/alerts/${notificationId}/mark-read`, {
      method: 'POST',
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
