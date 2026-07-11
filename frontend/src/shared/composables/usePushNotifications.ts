import { computed, ref } from 'vue'
import { apiRequest } from '@/shared/api/client.api'
import type {
  PushSubscriptionRequest,
  SingleResponsePushSubscriptionItem,
  VapidPublicKeyResponse
} from '@/shared/api/generated/types.gen'

// Module-level (singleton) state: every usePushNotifications() call anywhere
// in the app shares one source of truth for permission/subscribed state,
// mirroring useSystemNotifications' module-level notifications ref.
const permission = ref<NotificationPermission>(
  typeof Notification !== 'undefined' ? Notification.permission : 'denied'
)
const isSubscribed = ref(false)
const isBusy = ref(false)

const isSupported =
  typeof window !== 'undefined' && 'serviceWorker' in navigator && 'PushManager' in window

const urlBase64ToUint8Array = (base64: string): Uint8Array<ArrayBuffer> => {
  const padding = '='.repeat((4 - (base64.length % 4)) % 4)
  const base64Safe = (base64 + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(base64Safe)
  const bytes = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i += 1) {
    bytes[i] = raw.charCodeAt(i)
  }
  return bytes
}

const getRegistration = (): Promise<ServiceWorkerRegistration> => navigator.serviceWorker.ready

/** Registers the built service worker. No-op in dev (there is no injected
 * manifest to serve — see vite.config.ts devOptions) and when the browser
 * doesn't support service workers at all. */
export const registerServiceWorker = (): void => {
  if (import.meta.env.DEV || !isSupported) {
    return
  }
  void navigator.serviceWorker.register('/sw.js', { type: 'module' }).then((registration) => {
    registration.pushManager.getSubscription().then((subscription) => {
      isSubscribed.value = subscription !== null
    })
  })
}

export function usePushNotifications() {
  const isDenied = computed(() => permission.value === 'denied')
  const canEnable = computed(() => isSupported && !isDenied.value && !isSubscribed.value)

  const refreshSubscriptionState = async () => {
    if (!isSupported) {
      return
    }
    const registration = await getRegistration()
    const subscription = await registration.pushManager.getSubscription()
    isSubscribed.value = subscription !== null
  }

  /** Must be called from a click handler: browsers only grant the
   * Notification permission prompt in response to a user gesture. */
  const enable = async () => {
    if (!isSupported || isBusy.value) {
      return
    }
    isBusy.value = true
    try {
      permission.value = await Notification.requestPermission()
      if (permission.value !== 'granted') {
        return
      }

      const { public_key: vapidPublicKey } = await apiRequest<VapidPublicKeyResponse>(
        '/push/vapid-public-key'
      )
      const registration = await getRegistration()
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidPublicKey)
      })

      const json = subscription.toJSON()
      await apiRequest<SingleResponsePushSubscriptionItem>('/push/subscriptions', {
        method: 'POST',
        body: {
          endpoint: subscription.endpoint,
          keys: { p256dh: json.keys?.p256dh ?? '', auth: json.keys?.auth ?? '' }
        } satisfies PushSubscriptionRequest
      })
      isSubscribed.value = true
    } finally {
      isBusy.value = false
    }
  }

  const disable = async () => {
    if (!isSupported || isBusy.value) {
      return
    }
    isBusy.value = true
    try {
      const registration = await getRegistration()
      const subscription = await registration.pushManager.getSubscription()
      if (!subscription) {
        isSubscribed.value = false
        return
      }
      const endpoint = subscription.endpoint
      await subscription.unsubscribe()
      await apiRequest('/push/subscriptions', { method: 'DELETE', body: { endpoint } })
      isSubscribed.value = false
    } finally {
      isBusy.value = false
    }
  }

  return {
    isSupported,
    permission,
    isDenied,
    isSubscribed,
    canEnable,
    isBusy,
    enable,
    disable,
    refreshSubscriptionState
  }
}
