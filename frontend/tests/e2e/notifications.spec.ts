import { test, expect } from './support/fixtures'
import { loginAsRegistrar } from './support/auth'
import {
  cleanupDirectionsByBaseNo,
  createDirection,
  createSample,
  currentUser,
  rejectSample
} from './support/api'

const NOTIFICATION_BASE_NO = 900601

test.describe('SSE notifications on sample rejection (flow #15)', () => {
  test.beforeEach(async ({ request }) => {
    await cleanupDirectionsByBaseNo(request, NOTIFICATION_BASE_NO)
  })

  test('registrator sees a live SSE notification when a sample is rejected, and can mark it read', async ({
    page
  }) => {
    await loginAsRegistrar(page)
    // loginAsRegistrar already lands on /dashboard after the redirect.

    // Open the notifications slideover before triggering the event, so the
    // panel is listening on the SSE stream when the alert is emitted.
    await page.locator('[data-tour="dashboard-notifications"]').click()
    await expect(page.getByText('Notifications')).toBeVisible()

    // `page.request` shares the login session's cookies; the standalone
    // `request` fixture has its own empty cookie jar and can't call
    // authenticated endpoints like /auth/me.
    const me = await currentUser(page.request)
    const direction = await createDirection(page.request, {
      year_no: 2026,
      base_no: NOTIFICATION_BASE_NO
    })
    const sample = await createSample(page.request, {
      name: 'SSE notification sample',
      direction_id: direction.id
    })
    const reason = `e2e SSE check ${Date.now()}`
    const rejectResponse = await rejectSample(page.request, sample.id, me.id, reason)
    expect(rejectResponse.ok()).toBeTruthy()

    const notification = page.getByText(reason, { exact: false }).last()
    await expect(notification).toBeVisible({ timeout: 15_000 })

    const notificationRow = page.locator('div').filter({ hasText: reason }).last()
    await notificationRow.getByRole('button', { name: 'Mark as read' }).click()

    await page.getByRole('tab', { name: /Read/ }).click()
    await expect(page.getByText(reason).last()).toBeVisible()
  })
})
