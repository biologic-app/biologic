import type { Page } from '@playwright/test'

/**
 * Client-side SPA navigation via the sidebar, instead of `page.goto()`.
 * `page.goto()` forces a hard page reload — in this sandbox that re-fetches
 * everything including several external icon/font requests that are blocked
 * by the outbound network policy and only fail after a slow timeout, turning
 * every reload into a ~10s+ operation. The app is already loaded and
 * authenticated after login, so just click the nav link like a real user.
 */
async function clickNavLink(page: Page, name: string) {
  await page.getByRole('link', { name, exact: true }).click()
}

export async function goToDirections(page: Page) {
  await clickNavLink(page, 'Directions')
}

export async function goToSamples(page: Page) {
  await clickNavLink(page, 'Samples')
}

export async function goToProtocols(page: Page) {
  await clickNavLink(page, 'Protocols')
}

export async function goToDashboard(page: Page) {
  await clickNavLink(page, 'Home')
}
