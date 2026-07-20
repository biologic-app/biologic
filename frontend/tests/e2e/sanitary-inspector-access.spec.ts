import { test, expect } from './support/fixtures'
import { loginAsSanitaryInspector } from './support/auth'
import { goToDirections, goToSamples } from './support/nav'
import {
  cleanupDirectionsByBaseNo,
  createDirection,
  createSample,
  currentUser,
  rejectSample
} from './support/api'

// Verifies the sanitary inspector (СВ) role stays strictly read-only, per
// docs/flows/sanitary-doctor.flow.md: can see directions/samples/audit/
// conclusions/notifications, cannot create/edit/delete anything, and has no
// access to Research or most reference-data dictionaries. This is an access
// audit, not a workflow test — the role never mutates domain data.
const DIRECTIONS_BASE_NO = 990701
const SAMPLES_BASE_NO = 990702
const NOTIFY_BASE_NO = 990703

test.describe('sanitary inspector — read-only access (docs/flows/sanitary-doctor.flow.md)', () => {
  test.beforeEach(async ({ request }) => {
    for (const baseNo of [DIRECTIONS_BASE_NO, SAMPLES_BASE_NO, NOTIFY_BASE_NO]) {
      await cleanupDirectionsByBaseNo(request, baseNo)
    }
  })

  test('logs in and sees a dashboard with locked-out nav items', async ({ page }) => {
    await loginAsSanitaryInspector(page)

    await expect(page.getByRole('link', { name: 'Directions', exact: true })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Samples', exact: true })).toBeVisible()

    // Research requires research:view, which sanitary_inspector does not have —
    // the nav item renders with a lock icon and must not navigate.
    const researchLink = page.getByText('Research', { exact: true })
    await expect(researchLink).toBeVisible()
    await researchLink.click({ force: true }).catch(() => undefined)
    await expect(page).not.toHaveURL(/\/research$/)
  })

  test('directions: can view, cannot create, edit, delete, or run workflow commands', async ({
    page,
    request
  }) => {
    await createDirection(request, { year_no: 2026, base_no: DIRECTIONS_BASE_NO })
    await loginAsSanitaryInspector(page)
    await goToDirections(page)

    const createButton = page.getByRole('button', { name: 'Создать' })
    await expect(createButton).toBeDisabled()

    await page.getByTestId('crud-search-input').fill(String(DIRECTIONS_BASE_NO))
    const row = page.locator('tbody tr').filter({ hasText: String(DIRECTIONS_BASE_NO) })
    await expect(row.first()).toBeVisible()

    await row.first().click({ button: 'right' })
    await expect(page.getByRole('menuitem', { name: 'Просмотр' })).toBeEnabled()
    await expect(page.getByRole('menuitem', { name: 'Редактировать' })).toBeDisabled()
    await expect(page.getByRole('menuitem', { name: 'Удалить' })).toBeDisabled()
    // Workflow commands (register/reject/…) still render in the menu — same
    // "always visible, disabled with a lock icon" pattern as every other
    // locked action in this app — but canRunCommandOnRow disables them since
    // the role has no command permissions.
    await expect(
      page.getByRole('menuitem', { name: /Зарегистрировать направление/ })
    ).toBeDisabled()
    await page.keyboard.press('Escape')

    await row.first().click({ button: 'right' })
    await page.getByRole('menuitem', { name: 'Просмотр' }).click()
    await expect(page.getByRole('tab', { name: 'Карточка' })).toBeVisible()
    // The in-card edit button is a second entry point into the same PATCH —
    // must also be gated (fixed in this session), not just the row menu. Also
    // assert Сохранить/Отменить are absent, not just Редактировать: an earlier
    // version of this fix used `v-if="!editing && canEditEntity"` with no
    // matching change to the `v-else`, so the card fell straight into the
    // "editing" (Сохранить/Отменить) branch for anyone lacking edit rights —
    // exactly backwards from the intended read-only view.
    await expect(page.getByRole('button', { name: 'Редактировать' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Сохранить' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Отменить' })).toHaveCount(0)

    // The technical audit is now a trailing icon button (entity modal rework),
    // not a tab — clicking it switches the modal body to the audit timeline,
    // which renders a "Технический аудит" heading.
    await page.getByTestId('entity-detail-technical-tab').click()
    await expect(page.getByRole('heading', { name: 'Технический аудит' })).toBeVisible()
  })

  test('samples: no create button, row actions locked', async ({ page, request }) => {
    const direction = await createDirection(request, { year_no: 2026, base_no: SAMPLES_BASE_NO })
    await createSample(request, { name: 'SanInspector read-only sample', direction_id: direction.id })
    await loginAsSanitaryInspector(page)
    await goToSamples(page)

    await expect(page.getByRole('heading', { name: 'Образцы' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Создать' })).toHaveCount(0)

    await page.getByTestId('crud-search-input').fill('SanInspector read-only sample')
    const row = page.locator('tbody tr').filter({ hasText: 'SanInspector read-only sample' })
    await expect(row.first()).toBeVisible()

    await row.first().click({ button: 'right' })
    await expect(page.getByRole('menuitem', { name: 'Просмотр' })).toBeEnabled()
    await expect(page.getByRole('menuitem', { name: 'Редактировать' })).toBeDisabled()
    await expect(page.getByRole('menuitem', { name: 'Удалить' })).toBeDisabled()
    await expect(page.getByRole('menuitem', { name: /Забраковать образец/ })).toBeDisabled()
  })

  test('reference data: only Заключения is reachable, everything else is locked', async ({
    page
  }) => {
    await loginAsSanitaryInspector(page)
    // "Reference data" has nested children, so the sidebar renders it as an
    // expand trigger (button), not a direct link like "Directions"/"Samples".
    await page.getByText('Reference data', { exact: true }).click()

    await expect(page.getByRole('link', { name: 'Заключения', exact: true })).toBeVisible()

    const objectsLink = page.getByText('Объекты', { exact: true })
    await expect(objectsLink).toBeVisible()
    await objectsLink.click({ force: true }).catch(() => undefined)
    await expect(page).not.toHaveURL(/objects/)
  })

  test('notifications: broadcast alerts are visible and can be marked read', async ({ page }) => {
    await loginAsSanitaryInspector(page)
    await page.locator('[data-tour="dashboard-notifications"]').click()
    await expect(page.getByRole('heading', { name: 'Notifications' })).toBeVisible()

    const me = await currentUser(page.request)
    const direction = await createDirection(page.request, {
      year_no: 2026,
      base_no: NOTIFY_BASE_NO
    })
    const sample = await createSample(page.request, {
      name: 'SanInspector notification sample',
      direction_id: direction.id
    })
    const reason = `san inspector broadcast check ${Date.now()}`
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
