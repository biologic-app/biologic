import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test, expect } from './support/fixtures'
import { loginAsRegistrar } from './support/auth'
import { cleanupDirectionsByBaseNo } from './support/api'
import { goToDirections } from './support/nav'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

const EXCEL_BASE_NO_MULTI = 900101 // 2 samples
const EXCEL_BASE_NO_SINGLE = 900102 // 1 sample
// Baked into the real document's header cell ("№ 000000460") — the legacy
// .xls parser reads it verbatim as base_no, it isn't test-controlled.
const LEGACY_XLS_BASE_NO = 460

const fixturesDir = path.join(__dirname, 'fixtures')

/**
 * Drives the direction-creation wizard through its import branch: opens it from
 * the "Создать направление" button, picks the "Импорт из файла" mode, uploads
 * the given Excel/.xls file (the hidden <input> takes the file directly), and
 * runs the import. Leaves the wizard on the "Предпросмотр" (review) step, where
 * the freshly-created draft directions are shown — the caller closes it with
 * Escape (the directions are already persisted as draft) or continues.
 *
 * The old single import menu (data-testid="direction-import-menu-trigger") and
 * the separate Excel/JSON/legacy menu items are gone: import is now a stepper
 * wizard (DirectionWizard.vue) that only accepts Excel (.xlsx/.xls) — the
 * backend routes a .xls to the legacy parser by extension. JSON import stays a
 * machine-to-machine endpoint and is no longer offered in the UI.
 */
async function importFileViaWizard(page: import('@playwright/test').Page, file: string) {
  await page.getByTestId('direction-create-open').click()
  await page.getByTestId('direction-mode-import').click()
  await page.getByTestId('import-excel-input').setInputFiles(file)
  // The dropzone flips to "Файл готов к импорту" and enables "Далее".
  await expect(page.getByText('Файл готов к импорту')).toBeVisible()
  await page.getByTestId('direction-import-submit').click()
  // runImport POSTs to /directions/import-excel (draft directions + samples)
  // and advances to the review step, which renders a card per created
  // direction.
  await expect(page.getByTestId('direction-review-card').first()).toBeVisible({ timeout: 30_000 })
}

async function closeWizard(page: import('@playwright/test').Page) {
  // The wizard UModal is dismissible once the import has finished; Escape closes
  // it, leaving the imported directions in place (draft).
  await page.keyboard.press('Escape')
  await expect(page.getByTestId('direction-review-card')).toHaveCount(0)
}

test.describe('direction import (flow #2, #3)', () => {
  test.beforeEach(async ({ request }) => {
    for (const baseNo of [EXCEL_BASE_NO_MULTI, EXCEL_BASE_NO_SINGLE, LEGACY_XLS_BASE_NO]) {
      await cleanupDirectionsByBaseNo(request, baseNo)
    }
  })

  test('imports directions and samples from an Excel file via the creation wizard', async ({
    page
  }) => {
    await loginAsRegistrar(page)
    await goToDirections(page)

    await importFileViaWizard(page, path.join(fixturesDir, 'directions-import.xlsx'))

    // The review step lists the created draft directions with their sample
    // names — the 2-sample direction (900101) shows both "Проба A"/"Проба Б"
    // and an "Образцов: 2" badge.
    await expect(page.getByText(`№ 2026-${EXCEL_BASE_NO_MULTI}`)).toBeVisible()
    await expect(page.getByText('Проба A')).toBeVisible()
    await expect(page.getByText('Проба Б')).toBeVisible()
    await expect(page.getByText('Образцов: 2')).toBeVisible()

    await closeWizard(page)

    // The imported direction is in the table in draft status.
    await page.getByTestId('crud-search-input').fill(String(EXCEL_BASE_NO_MULTI))
    const row = page.locator('tbody tr').filter({ hasText: String(EXCEL_BASE_NO_MULTI) })
    await expect(row.first()).toBeVisible()
    await expect(row.first().getByText('Черновик')).toBeVisible()
  })

  test('an imported direction shows its samples and can be edited while in draft', async ({
    page
  }) => {
    await loginAsRegistrar(page)
    await goToDirections(page)

    await importFileViaWizard(page, path.join(fixturesDir, 'directions-import.xlsx'))
    await closeWizard(page)

    await page.getByTestId('crud-search-input').fill(String(EXCEL_BASE_NO_MULTI))
    const row = page.locator('tbody tr').filter({ hasText: String(EXCEL_BASE_NO_MULTI) })
    await expect(row.first()).toBeVisible()
    await row.first().click({ button: 'right' })
    await page.getByRole('menuitem', { name: 'Просмотр' }).click()

    await expect(page.getByRole('tab', { name: 'Карточка' })).toBeVisible()
    // The direction's related tab is labelled "Образцы" (entity modal rework);
    // its body is a table of the sample rows.
    await page.getByRole('tab', { name: /Образцы/ }).click()
    await expect(page.getByText('Проба A')).toBeVisible()
    await expect(page.getByText('Проба Б')).toBeVisible()

    await page.getByRole('tab', { name: 'Карточка' }).click()
    await page.getByRole('button', { name: 'Редактировать' }).click()
    // "Год" is a select (USelectMenu, rendered as a "Show popup" button), not a
    // free-text input, after the field-config change — pick a different year
    // from the dropdown to prove the draft is editable.
    const yearFieldRow = page.locator('dl > div').filter({ hasText: 'Год' }).first()
    await yearFieldRow.getByRole('button').click()
    await page.getByRole('option', { name: '2025', exact: true }).click()
    await page.getByRole('button', { name: 'Сохранить' }).click()
    await expect(yearFieldRow).toContainText('2025')
  })

  test('imports a real institutional .xls direction document (legacy scanned-form layout)', async ({
    page
  }) => {
    await loginAsRegistrar(page)
    await goToDirections(page)

    // The legacy .xls goes through the same "Импорт из файла" wizard branch —
    // the backend routes a .xls file to the legacy parser by extension.
    await importFileViaWizard(page, path.join(fixturesDir, 'legacy-direction.xls'))

    // The review card title is "№ <year>-460"; the year comes from the parsed
    // document header, so match on the base_no suffix rather than a fixed year.
    await expect(page.getByTestId('direction-review-card').first()).toContainText(
      String(LEGACY_XLS_BASE_NO)
    )

    await closeWizard(page)

    await page.getByTestId('crud-search-input').fill(String(LEGACY_XLS_BASE_NO))
    const row = page.locator('tbody tr').filter({ hasText: String(LEGACY_XLS_BASE_NO) })
    await expect(row.first()).toBeVisible()
    await expect(row.first().getByText('Черновик')).toBeVisible()

    await row.first().click({ button: 'right' })
    await page.getByRole('menuitem', { name: 'Просмотр' }).click()
    await page.getByRole('tab', { name: /Образцы/ }).click()
    // Related tab paginates 20 rows at a time (see RELATED_PAGE_SIZE); 94
    // imported samples means the first page is full and "Load more" shows.
    await expect(page.getByText('Грецкий орех 130 гр')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Загрузить ещё' })).toBeVisible()
  })
})
