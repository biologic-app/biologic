/**
 * Registers the built service worker for PWA precaching and installability.
 * No-op in dev (VitePWA devOptions are disabled, so there is no worker to
 * serve) and where the browser has no service-worker support.
 */
export const registerServiceWorker = (): void => {
  if (import.meta.env.DEV || !("serviceWorker" in navigator)) {
    return;
  }
  void navigator.serviceWorker.register("/sw.js", { type: "module" });
};
