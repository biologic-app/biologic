/**
 * Registers the built service worker for PWA precaching and installability, and
 * keeps it auto-updating so a new deployment replaces the cached app shell
 * without a manual hard-reload or storage clear.
 *
 * No-op in dev (VitePWA devOptions are disabled, so there is no worker to
 * serve) and where the browser has no service-worker support.
 *
 * The worker itself (src/sw.ts) skipWaiting()s on install and claims clients on
 * activate, so a freshly installed build takes control at once. This module
 * supplies the missing client half: it promotes a worker that is stuck
 * "waiting to activate", detects new builds (even in a tab left open for
 * hours), and reloads once when the new worker takes over so the fresh precache
 * is actually shown.
 */
export const registerServiceWorker = (): void => {
  if (import.meta.env.DEV || !("serviceWorker" in navigator)) {
    return;
  }

  // A page that loaded already under a worker gets `controllerchange` only when
  // a *new* build's worker takes over (sw.ts skipWaiting + clients.claim) — so
  // reload once to swap in the new precached shell. A first-visit install also
  // fires controllerchange via the initial claim, but nothing is stale then, so
  // that case is skipped to avoid an endless reload loop.
  const hadController = Boolean(navigator.serviceWorker.controller);
  let reloading = false;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (!hadController || reloading) {
      return;
    }
    reloading = true;
    window.location.reload();
  });

  // updateViaCache: 'none' forces update() to revalidate sw.js against the
  // network instead of the HTTP cache, so a new build is never masked by a
  // stale cached worker script.
  void navigator.serviceWorker
    .register("/sw.js", { type: "module", updateViaCache: "none" })
    .then((registration) => {
      // Force-activate a worker sitting in "waiting to activate" — one already
      // waiting now (installed before this promote logic shipped), or one that
      // installs later. sw.ts activates on the SKIP_WAITING message, which
      // fires controllerchange and the reload above.
      const promoteWaiting = (): void => {
        registration.waiting?.postMessage({ type: "SKIP_WAITING" });
      };
      promoteWaiting();
      registration.addEventListener("updatefound", () => {
        const installing = registration.installing;
        installing?.addEventListener("statechange", () => {
          if (installing.state === "installed") {
            promoteWaiting();
          }
        });
      });

      // The browser only re-checks sw.js on navigation; a tab left open never
      // navigates, so poll for a new deployment and re-check whenever the tab
      // is refocused. When update() finds one, the new worker installs, is
      // promoted, claims the page, and the controllerchange handler reloads it.
      const checkForUpdate = (): void => {
        void registration.update();
      };
      window.setInterval(checkForUpdate, 60_000);
      document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") {
          checkForUpdate();
        }
      });
    });
};
