/// <reference lib="webworker" />
import { precacheAndRoute, cleanupOutdatedCaches } from 'workbox-precaching'

declare const self: ServiceWorkerGlobalScope

// Injected by vite-plugin-pwa's injectManifest build step; empty in dev
// (devOptions.enabled is false — see vite.config.ts).
precacheAndRoute(self.__WB_MANIFEST)
cleanupOutdatedCaches()

self.skipWaiting()
self.addEventListener('activate', () => self.clients.claim())

interface PushPayload {
  title?: string
  body?: string
  url?: string
}

self.addEventListener('push', (event: PushEvent) => {
  const payload: PushPayload = event.data ? event.data.json() : {}
  const title = payload.title || 'Biologic LIMS'

  event.waitUntil(
    self.registration.showNotification(title, {
      body: payload.body,
      icon: '/icon-192.png',
      badge: '/icon-192.png',
      data: { url: payload.url || '/' }
    })
  )
})

self.addEventListener('notificationclick', (event: NotificationEvent) => {
  event.notification.close()
  const targetUrl = (event.notification.data as PushPayload | undefined)?.url || '/'

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      const existing = clients.find((client) => 'focus' in client)
      if (existing) {
        return existing.focus().then(() => {
          if ('navigate' in existing && typeof existing.navigate === 'function') {
            return existing.navigate(targetUrl)
          }
          return undefined
        })
      }
      return self.clients.openWindow(targetUrl)
    })
  )
})
