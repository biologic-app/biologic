/// <reference lib="webworker" />
import { precacheAndRoute, cleanupOutdatedCaches } from 'workbox-precaching'

declare const self: ServiceWorkerGlobalScope

// Injected by vite-plugin-pwa's injectManifest build step; empty in dev
// (devOptions.enabled is false — see vite.config.ts). Precaching is the only
// job of this worker: it keeps the app shell installable and loadable, while
// notifications are delivered in-app over SSE (no Web Push).
precacheAndRoute(self.__WB_MANIFEST)
cleanupOutdatedCaches()

// Activate a freshly installed build at once instead of waiting for every tab
// controlled by the old worker to close, then claim those tabs so the new
// precache serves them immediately. registerServiceWorker.ts reloads them on
// the resulting controllerchange. skipWaiting() lives in the install handler
// (not top-level) so it reliably fires while the worker is in the installing
// phase; clients.claim() is wrapped in waitUntil so activation awaits it.
self.addEventListener('install', () => {
  self.skipWaiting()
})
self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim())
})

// Escape hatch for a worker that installed *before* this auto-skip logic
// shipped and is stuck "waiting to activate": the page posts SKIP_WAITING to
// promote it (see registerServiceWorker.ts).
self.addEventListener('message', (event) => {
  const data = event.data as { type?: string } | null
  if (data?.type === 'SKIP_WAITING') {
    self.skipWaiting()
  }
})

// Focuses an already-open tab/window when the user clicks a system
// notification raised by showSystemNotification (useSystemNotifications.ts);
// falls back to opening a new window if none is open.
self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  event.waitUntil(
    (async () => {
      const clients = await self.clients.matchAll({ type: 'window', includeUncontrolled: true })
      const existing = clients[0]
      if (existing) {
        await existing.focus()
        return
      }
      await self.clients.openWindow('/')
    })()
  )
})
