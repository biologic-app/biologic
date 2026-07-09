import { test, expect } from './support/fixtures'
import { loginAsRegistrar } from './support/auth'
import { goToSamples } from './support/nav'
import { cleanupDirectionsByBaseNo, createDirection, createSample } from './support/api'

const CARD_REJECT_BASE_NO = 900401
const BULK_REJECT_BASE_NO = 900402

test.describe('sample list and lifecycle (flow #5, #11, #12, #13, #14)', () => {
  test.beforeEach(async ({ request }) => {
    for (const baseNo of [CARD_REJECT_BASE_NO, BULK_REJECT_BASE_NO]) {
      await cleanupDirectionsByBaseNo(request, baseNo)
    }
  })

  test('the samples page has no "create" button — samples are only created via a direction', async ({
    page
  }) => {
    await loginAsRegistrar(page)
    await goToSamples(page)

    await expect(page.getByRole('heading', { name: 'Образцы' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Создать' })).toHaveCount(0)
  })

  test('opens a sample card, rejects it, and sees the rejection in business and technical audit', async ({
    page,
    request
  }) => {
    await loginAsRegistrar(page)
    const direction = await createDirection(request, {
      year_no: 2026,
      base_no: CARD_REJECT_BASE_NO
    })
    const sample = await createSample(request, {
      name: 'Card reject sample',
      direction_id: direction.id
    })

    await goToSamples(page)
    await page.getByTestId('crud-search-input').fill(sample.name)
    const row = page.locator('tbody tr').filter({ hasText: sample.name })
    await expect(row.first()).toBeVisible()
    await expect(row.first().getByText('На регистрации')).toBeVisible()

    await row.first().click({ button: 'right' })
    await page.getByRole('menuitem', { name: /Просмотр/ }).click()
    await expect(page.getByRole('tab', { name: 'Карточка' })).toBeVisible()
    await page.getByRole('button', { name: 'Закрыть' }).click()

    await row.first().click({ button: 'right' })
    await page.getByRole('menuitem', { name: /REJ · Забраковать образец/ }).click()
    await page.getByLabel('Причина').fill('Повреждена упаковка')
    await page.getByRole('button', { name: 'Сохранить' }).click()
    await expect(page.getByText('Образцы помечены как брак').last()).toBeVisible()

    await page.getByTestId('crud-search-input').fill(sample.name)
    const rejectedRow = page.locator('tbody tr').filter({ hasText: sample.name })
    await expect(rejectedRow.first().getByText('Брак')).toBeVisible()

    await rejectedRow.first().click({ button: 'right' })
    await page.getByRole('menuitem', { name: /Просмотр/ }).click()
    await expect(page.getByText('Брак').first()).toBeVisible()
    await page.getByRole('tab', { name: 'Технический аудит' }).click()
    await expect(page.getByText('sample rejected').last()).toBeVisible()
  })

  test('rejects a sample via row-selection bulk action', async ({ page, request }) => {
    await loginAsRegistrar(page)
    const direction = await createDirection(request, {
      year_no: 2026,
      base_no: BULK_REJECT_BASE_NO
    })
    const sample = await createSample(request, {
      name: 'Bulk reject sample',
      direction_id: direction.id
    })

    await goToSamples(page)
    await page.getByTestId('crud-search-input').fill(sample.name)
    const row = page.locator('tbody tr').filter({ hasText: sample.name })
    await expect(row.first()).toBeVisible()

    await row.first().locator('[role="checkbox"], input[type="checkbox"]').first().click()
    await expect(page.getByText('1 выбрано')).toBeVisible()
    await page.getByRole('button', { name: 'Брак', exact: true }).click()
    await page.getByLabel('Причина').fill('Брак при массовой обработке')
    await page.getByRole('button', { name: 'Сохранить' }).click()
    await expect(page.getByText('Образцы помечены как брак').last()).toBeVisible()

    await page.getByTestId('crud-search-input').fill(sample.name)
    const rejectedRow = page.locator('tbody tr').filter({ hasText: sample.name })
    await expect(rejectedRow.first().getByText('Брак')).toBeVisible()
  })
})
