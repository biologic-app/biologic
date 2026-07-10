import { test, expect } from './support/fixtures'
import { loginAsRegistrar } from './support/auth'

/**
 * Web Push subscribe/unsubscribe through the real UI toggle.
 *
 * Requires the app to be served from a *production* build (`bun run build`
 * + `bun run preview`, or `E2E_BASE_URL` pointed at one) — the service
 * worker only registers when `import.meta.env.DEV` is false (see
 * `registerServiceWorker` in `usePushNotifications.ts`); `bun run dev` skips
 * it entirely, so this spec is a no-op against the plain dev server.
 *
 * `PushManager.subscribe`/`getSubscription` are mocked in-page: a real push
 * subscription needs a live browser push service (FCM/Mozilla) with
 * outbound network access this suite doesn't assume. The service worker
 * registration itself, the Notification permission flow and the
 * subscribe/unsubscribe HTTP calls to the backend are all real.
 */
test.describe('Web Push subscribe/unsubscribe (notifications context)', () => {
  test.beforeEach(async ({ context }) => {
    await context.grantPermissions(['notifications'])
    await context.addInitScript(() => {
      const fakeEndpoint = 'https://push.example/e2e-fake-subscription'
      const fakeSubscription = {
        endpoint: fakeEndpoint,
        toJSON: () => ({ keys: { p256dh: 'e2e-p256dh', auth: 'e2e-auth' } }),
        unsubscribe: async () => true
      }
      let subscribed: typeof fakeSubscription | null = null

      const patchPushManager = () => {
        const registration = (
          window.navigator.serviceWorker as unknown as { ready?: Promise<unknown> }
        ).ready
        if (!registration) {
          return
        }
        void registration.then((reg) => {
          const pushManager = (reg as { pushManager: PushManager }).pushManager
          pushManager.subscribe = async () => {
            subscribed = fakeSubscription
            return fakeSubscription as unknown as PushSubscription
          }
          pushManager.getSubscription = async () =>
            subscribed as unknown as PushSubscription | null
        })
      }
      patchPushManager()
    })
  })

  test('registrator enables and disables push notifications from the slideover', async ({
    page
  }) => {
    await loginAsRegistrar(page)

    await page.locator('[data-tour="dashboard-notifications"]').click()
    await expect(page.getByText('Notifications')).toBeVisible()

    const toggle = page.getByTestId('push-notifications-toggle')
    await expect(toggle).toBeVisible()

    const subscribeRequest = page.waitForRequest(
      (request) =>
        request.url().includes('/push/subscriptions') && request.method() === 'POST'
    )
    await toggle.click()
    const subscribeReq = await subscribeRequest
    const subscribeBody = subscribeReq.postDataJSON()
    expect(subscribeBody.endpoint).toBe('https://push.example/e2e-fake-subscription')
    expect(subscribeBody.keys).toEqual({ p256dh: 'e2e-p256dh', auth: 'e2e-auth' })

    await expect(toggle).toHaveAttribute('aria-checked', 'true')

    const unsubscribeRequest = page.waitForRequest(
      (request) =>
        request.url().includes('/push/subscriptions') && request.method() === 'DELETE'
    )
    await toggle.click()
    const unsubscribeReq = await unsubscribeRequest
    expect(unsubscribeReq.postDataJSON()).toEqual({
      endpoint: 'https://push.example/e2e-fake-subscription'
    })

    await expect(toggle).toHaveAttribute('aria-checked', 'false')
  })
})
