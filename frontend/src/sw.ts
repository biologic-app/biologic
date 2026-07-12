/// <reference lib="webworker" />
import { precacheAndRoute, cleanupOutdatedCaches } from 'workbox-precaching'

declare const self: ServiceWorkerGlobalScope

// Injected by vite-plugin-pwa's injectManifest build step; empty in dev
// (devOptions.enabled is false — see vite.config.ts). Precaching is the only
// job of this worker: it keeps the app shell installable and loadable, while
// notifications are delivered in-app over SSE (no Web Push).
precacheAndRoute(self.__WB_MANIFEST)
cleanupOutdatedCaches()

self.skipWaiting()
self.addEventListener('activate', () => self.clients.claim())
