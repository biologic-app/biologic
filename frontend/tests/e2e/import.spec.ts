import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test, expect } from './support/fixtures'
import { loginAsRegistrar } from './support/auth'
import { cleanupDirectionsByBaseNo } from './support/api'
import { goToDirections } from './support/nav'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

const EXCEL_BASE_NO_MULTI = 900101 // 2 samples
const EXCEL_BASE_NO_SINGLE = 900102 // 1 sample
const JSON_BASE_NO_MULTI = 900201
const JSON_BASE_NO_SINGLE = 900202
// Baked into the real document's header cell ("№ 000000460") — the legacy
// .xls parser reads it verbatim as base_no, it isn't test-controlled.
const LEGACY_XLS_BASE_NO = 460

const fixturesDir = path.join(__dirname, 'fixtures')

test.describe('direction import (flow #2, #3)', () => {
  test.beforeEach(async ({ request }) => {
    for (const baseNo of [
      EXCEL_BASE_NO_MULTI,
      EXCEL_BASE_NO_SINGLE,
      JSON_BASE_NO_MULTI,
      JSON_BASE_NO_SINGLE,
      LEGACY_XLS_BASE_NO
    ]) {
      await cleanupDirectionsByBaseNo(request, baseNo)
    }
  })

  test('imports directions and samples from an Excel file', async ({ page }) => {
    await loginAsRegistrar(page)
    await goToDirections(page)

    await page.getByTestId('direction-import-menu-trigger').click()
    const fileChooserPromise = page.waitForEvent('filechooser')
    await page.getByRole('menuitem', { name: 'Импортировать Excel' }).click()
    const fileChooser = await fileChooserPromise
    await fileChooser.setFiles(path.join(fixturesDir, 'directions-import.xlsx'))

    await expect(page.getByText('Импорт направлений завершён').last()).toBeVisible()
    await expect(page.getByText(/Направлений: 2, образцов: 3/).last()).toBeVisible()

    await page.getByTestId('crud-search-input').fill(String(EXCEL_BASE_NO_MULTI))
    const row = page.locator('tbody tr').filter({ hasText: String(EXCEL_BASE_NO_MULTI) })
    await expect(row.first()).toBeVisible()
    await expect(row.first().getByText('Черновик')).toBeVisible()
  })

  test('imports directions and samples from a JSON file (fallback path)', async ({ page }) => {
    await loginAsRegistrar(page)
    await goToDirections(page)

    await page.getByTestId('direction-import-menu-trigger').click()
    const fileChooserPromise = page.waitForEvent('filechooser')
    await page.getByRole('menuitem', { name: /Импортировать JSON/ }).click()
    const fileChooser = await fileChooserPromise
    await fileChooser.setFiles(path.join(fixturesDir, 'directions-import.json'))

    await expect(page.getByText('Импорт направлений завершён').last()).toBeVisible()
    await expect(page.getByText(/Направлений: 2, образцов: 3/).last()).toBeVisible()

    await page.getByTestId('crud-search-input').fill(String(JSON_BASE_NO_MULTI))
    const row = page.locator('tbody tr').filter({ hasText: String(JSON_BASE_NO_MULTI) })
    await expect(row.first()).toBeVisible()
    await expect(row.first().getByText('Черновик')).toBeVisible()
  })

  test('an imported direction shows its samples and can be edited while in draft', async ({
    page
  }) => {
    await loginAsRegistrar(page)
    await goToDirections(page)

    await page.getByTestId('direction-import-menu-trigger').click()
    const fileChooserPromise = page.waitForEvent('filechooser')
    await page.getByRole('menuitem', { name: 'Импортировать Excel' }).click()
    const fileChooser = await fileChooserPromise
    await fileChooser.setFiles(path.join(fixturesDir, 'directions-import.xlsx'))
    await expect(page.getByText('Импорт направлений завершён').last()).toBeVisible()

    await page.getByTestId('crud-search-input').fill(String(EXCEL_BASE_NO_MULTI))
    const row = page.locator('tbody tr').filter({ hasText: String(EXCEL_BASE_NO_MULTI) })
    await expect(row.first()).toBeVisible()
    await row.first().click({ button: 'right' })
    await page.getByRole('menuitem', { name: 'Просмотр' }).click()

    await expect(page.getByRole('tab', { name: 'Карточка' })).toBeVisible()
    await page.getByRole('tab', { name: 'Связанные' }).click()
    await expect(page.getByText('2 записей')).toBeVisible()

    await page.getByRole('tab', { name: 'Карточка' }).click()
    await page.getByRole('button', { name: 'Редактировать' }).click()
    const yearFieldRow = page.locator('dl > div').filter({ hasText: 'Год' }).first()
    await yearFieldRow.locator('input').fill('2027')
    await page.getByRole('button', { name: 'Сохранить' }).click()
    await expect(yearFieldRow).toContainText('2027')
  })

  test('imports a real institutional .xls direction document (legacy scanned-form layout)', async ({
    page
  }) => {
    await loginAsRegistrar(page)
    await goToDirections(page)

    await page.getByTestId('direction-import-menu-trigger').click()
    const fileChooserPromise = page.waitForEvent('filechooser')
    // The legacy .xls now goes through the single "Импортировать Excel" entry —
    // the backend routes a .xls file to the legacy parser (type=xlsx, dispatched
    // by extension), so there is no longer a separate legacy menu item.
    await page.getByRole('menuitem', { name: 'Импортировать Excel' }).click()
    const fileChooser = await fileChooserPromise
    await fileChooser.setFiles(path.join(fixturesDir, 'legacy-direction.xls'))

    await expect(page.getByText('Импорт направлений завершён').last()).toBeVisible()
    await expect(page.getByText(/образцов: 94/).last()).toBeVisible()

    await page.getByTestId('crud-search-input').fill(String(LEGACY_XLS_BASE_NO))
    const row = page.locator('tbody tr').filter({ hasText: String(LEGACY_XLS_BASE_NO) })
    await expect(row.first()).toBeVisible()
    await expect(row.first().getByText('Черновик')).toBeVisible()

    await row.first().click({ button: 'right' })
    await page.getByRole('menuitem', { name: 'Просмотр' }).click()
    await page.getByRole('tab', { name: 'Связанные' }).click()
    // Related tab paginates 20 rows at a time (see RELATED_PAGE_SIZE);
    // 94 imported samples means the first page is full and "Load more" shows.
    await expect(page.getByText('20 записей')).toBeVisible()
    await expect(page.getByText('Грецкий орех 130 гр')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Загрузить ещё' })).toBeVisible()
  })
})
