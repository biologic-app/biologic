import type { Page } from '@playwright/test'

export const REGISTRATOR = { username: 'registrator', password: 'registrator123' }
export const SANITARY_INSPECTOR = { username: 'sandoctor', password: 'sandoctor123' }
export const LAB_DOCTOR = { username: 'doctor', password: 'doctor123' }

/**
 * Dismisses the first-run product tour (driver.js) and the cookie-consent
 * toast. The toast auto-dismisses on its own after a few seconds, so the
 * click is best-effort with a short timeout — without it, a click racing the
 * toast's own fade-out can hang retrying against a detached element for the
 * whole test budget and take the page down with it.
 */
export async function dismissOnboarding(page: Page) {
  await page.waitForTimeout(300)
  await page.keyboard.press('Escape')
  await page
    .getByRole('button', { name: 'Decline' })
    .click({ timeout: 2000 })
    .catch(() => undefined)

  // The driver.js product tour (TourMenu.vue → startAutostart on mount) mounts
  // *asynchronously*, only after the dashboard summary request resolves — so a
  // single early Escape can fire before the tour exists and miss it entirely,
  // leaving a full-viewport `.driver-overlay` that silently intercepts every
  // later click (observed as nav-link clicks timing out). Give the overlay a
  // moment to appear, then press Escape until it actually detaches.
  const overlay = page.locator('.driver-overlay')
  await overlay
    .first()
    .waitFor({ state: 'visible', timeout: 3000 })
    .catch(() => undefined)
  for (let attempt = 0; attempt < 12 && (await overlay.count()) > 0; attempt++) {
    await page.keyboard.press('Escape')
    await page.waitForTimeout(250)
  }
}

/**
 * Occasionally the SPA lands on an empty shell after the post-login redirect
 * (an async render race, not something this suite is responsible for fixing)
 * — one reload is enough to recover, so confirm the sidebar actually mounted
 * before moving on instead of building every test on a blank page.
 */
async function ensureAppShellRendered(page: Page) {
  const homeLink = page.getByRole('link', { name: 'Home' })
  try {
    await homeLink.waitFor({ state: 'visible', timeout: 8000 })
  } catch {
    await page.reload()
    await homeLink.waitFor({ state: 'visible', timeout: 15000 })
  }
}

/** Logs in through the real /login form (manual credential entry) as the given user. */
export async function loginAs(page: Page, credentials: { username: string; password: string }) {
  await page.goto('/login')
  await page.getByLabel('Username').fill(credentials.username)
  await page.getByLabel('Password').fill(credentials.password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await page.waitForURL('**/dashboard')
  await ensureAppShellRendered(page)
  await dismissOnboarding(page)
}

/** Logs in through the real /login form (manual credential entry), as the registrar. */
export async function loginAsRegistrar(page: Page) {
  await loginAs(page, REGISTRATOR)
}

/** Logs in through the real /login form (manual credential entry), as the sanitary inspector. */
export async function loginAsSanitaryInspector(page: Page) {
  await loginAs(page, SANITARY_INSPECTOR)
}

/** Logs in through the real /login form (manual credential entry), as the lab doctor (ВЛ, role_key=lab_doctor). */
export async function loginAsLabDoctor(page: Page) {
  await loginAs(page, LAB_DOCTOR)
}
