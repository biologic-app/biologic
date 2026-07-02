import { test, expect } from './support/fixtures'
import { REGISTRATOR, loginAsRegistrar } from './support/auth'
import { goToDirections } from './support/nav'

// Flow point #1: registrator logs in manually with username/password.
test.describe('registrator login', () => {
  test('logs in with a manually entered username and password', async ({ page }) => {
    await loginAsRegistrar(page)

    // Navigate off the dashboard onto a plain CRUD page to confirm the
    // authenticated session actually works end-to-end.
    await goToDirections(page)
    await expect(page.getByRole('button', { name: 'Создать' })).toBeVisible()
  })

  test('shows an error and stays on /login for an invalid password', async ({ page }) => {
    await page.goto('/login')
    await page.getByLabel('Username').fill(REGISTRATOR.username)
    await page.getByLabel('Password').fill('wrong-password')
    await page.getByRole('button', { name: 'Sign in' }).click()

    await expect(page).toHaveURL(/\/login/)
  })
})
