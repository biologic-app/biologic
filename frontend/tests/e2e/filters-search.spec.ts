import { test, expect } from './support/fixtures'
import { loginAsRegistrar } from './support/auth'
import { goToDirections } from './support/nav'
import { cleanupDirectionsByBaseNo, createDirection } from './support/api'

const FILTER_BASE_NO = 900501
const SEARCH_BASE_NO = 900502

test.describe('filters and full-text search (flow #8, #9)', () => {
  test.beforeEach(async ({ request }) => {
    for (const baseNo of [FILTER_BASE_NO, SEARCH_BASE_NO]) {
      await cleanupDirectionsByBaseNo(request, baseNo)
    }
  })

  test('filters directions by a field value (number) and by status', async ({
    page,
    request
  }) => {
    await loginAsRegistrar(page)
    await createDirection(request, { year_no: 2026, base_no: FILTER_BASE_NO })

    await goToDirections(page)
    await page.getByRole('button', { name: 'Фильтр' }).click()
    await page.getByPlaceholder('Номер').fill(String(FILTER_BASE_NO))
    await page.getByRole('button', { name: 'Применить' }).click()

    const row = page.locator('tbody tr').filter({ hasText: String(FILTER_BASE_NO) })
    await expect(row.first()).toBeVisible()

    await page.getByRole('button', { name: 'Фильтр' }).click()
    await page.getByRole('button', { name: 'Сбросить' }).click()
  })

  test('finds a direction using the full-text search box', async ({ page, request }) => {
    await loginAsRegistrar(page)
    await createDirection(request, { year_no: 2026, base_no: SEARCH_BASE_NO })

    await goToDirections(page)
    await page.getByTestId('crud-search-input').fill(String(SEARCH_BASE_NO))

    const row = page.locator('tbody tr').filter({ hasText: String(SEARCH_BASE_NO) })
    await expect(row.first()).toBeVisible()
  })
})
