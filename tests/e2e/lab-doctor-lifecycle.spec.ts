import type { APIRequestContext } from '@playwright/test'
import { test, expect } from './support/fixtures'
import { loginAsLabDoctor } from './support/auth'
import { goToDashboard, goToResearch, goToSamples, goToTests } from './support/nav'
import {
  assignResearch,
  cleanupDirectionsByBaseNo,
  confirmResearch,
  createDirection,
  createIndicator,
  createResearchGoal,
  createSample,
  currentUser,
  deleteIndicator,
  deleteResearchGoal,
  firstReferenceItem,
  registerSample,
  startResearch
} from './support/api'

// Full lifecycle for the lab doctor (ВЛ, role_key=lab_doctor, account
// doctor/doctor123) per docs/flows/lab-doctor.flow.md: research
// confirm/start, tests start/complete (with research auto-completing once
// every test is terminal), tests requeue/reject, sample reject (with the
// SSE notification it fires) and research reject, plus the shared
// dashboard. Base_no ranges are unique per test for isolation, matching the
// convention in direction-lifecycle.spec.ts / sample-lifecycle.spec.ts.
const RESEARCH_TESTS_BASE_NO = 930101
const TEST_REQUEUE_REJECT_BASE_NO = 930102
const SAMPLE_REJECT_BASE_NO = 930103
const RESEARCH_REJECT_BASE_NO = 930104

/** Creates a dedicated research_goal with exactly one indicator, so
 * `assign-research` produces exactly one `tests` row — needed to make the
 * "last test completes -> research auto-completes" assertion deterministic
 * (a goal from seed/reference data may carry any number of indicators). */
async function createSingleIndicatorGoal(request: APIRequestContext, labId: string) {
  const suffix = `${Date.now()}-${Math.floor(Math.random() * 1000)}`
  const goal = await createResearchGoal(request, {
    code: `E2E-LD-${suffix}`,
    name: 'E2E lab doctor goal',
    lab_id: labId
  })
  // NOTE: POST /indicators forbids `lab_id` (extra_forbidden) — the indicator
  // inherits its lab through the research_goal, so only name +
  // research_goal_id are sent. The goal still needs an explicit lab_id.
  // The indicator name is made unique so the single generated `tests` row can
  // be located by it (the /tests table renders an extra structural <tr>, so an
  // exact row *count* is unreliable — filter by this text instead).
  const indicatorName = `E2E VL indicator ${suffix}`
  const indicator = await createIndicator(request, {
    name: indicatorName,
    research_goal_id: goal.id
  })
  return { goal, indicator, indicatorName }
}

test.describe('lab doctor (ВЛ) lifecycle (docs/flows/lab-doctor.flow.md)', () => {
  test.beforeEach(async ({ request }) => {
    for (const baseNo of [
      RESEARCH_TESTS_BASE_NO,
      TEST_REQUEUE_REJECT_BASE_NO,
      SAMPLE_REJECT_BASE_NO,
      RESEARCH_REJECT_BASE_NO
    ]) {
      await cleanupDirectionsByBaseNo(request, baseNo)
    }
  })

  test('research: confirm and start reflect in UI and technical audit; tests: start/complete auto-completes the research', async ({
    page
  }) => {
    await loginAsLabDoctor(page)
    const me = await currentUser(page.request)
    const sampleType = await firstReferenceItem(page.request, 'sample_types')
    const lab = await firstReferenceItem(page.request, 'labs')
    const { goal, indicator, indicatorName } = await createSingleIndicatorGoal(page.request, lab.id)

    const direction = await createDirection(page.request, {
      year_no: 2026,
      base_no: RESEARCH_TESTS_BASE_NO
    })
    const sample = await createSample(page.request, {
      name: 'LabDoctor lifecycle sample',
      direction_id: direction.id,
      sample_type_id: sampleType.id
    })
    const comment = `E2E lab doctor research ${Date.now()}`
    const assignResponse = await assignResearch(page.request, {
      sample_id: sample.id,
      actor_id: me.id,
      research_goal_id: goal.id,
      comment
    })
    expect(assignResponse.ok()).toBeTruthy()
    const research = (await assignResponse.json()).data as { id: string }
    // Register the sample (pending -> registered) so research.start moves it to
    // in_progress; otherwise completing the last test cascades the sample
    // pending -> analyzed, which is an invalid transition and rolls the whole
    // `complete` command back (409) — a pending sample can't be "analyzed".
    await registerSample(page.request, sample.id, me.id, new Date().toISOString())

    // --- Research: подтвердить (draft -> ordered) ---
    await goToResearch(page)
    await page.getByTestId('crud-search-input').fill(comment)
    const draftRow = page.locator('tbody tr').filter({ hasText: comment })
    await expect(draftRow.first()).toBeVisible()
    await expect(draftRow.first().getByText('Черновик')).toBeVisible()

    await draftRow.first().click({ button: 'right' })
    await page.getByRole('menuitem', { name: /CNF · Подтвердить исследование/ }).click()
    await expect(page.getByText('Исследования подтверждены').last()).toBeVisible()

    await page.getByTestId('crud-search-input').fill(comment)
    const orderedRow = page.locator('tbody tr').filter({ hasText: comment })
    await expect(orderedRow.first().getByText('Запланировано')).toBeVisible()

    await orderedRow.first().click({ button: 'right' })
    await page.getByRole('menuitem', { name: 'Просмотр' }).click()
    await expect(page.getByText('Запланировано').first()).toBeVisible()
    await page.getByRole('tab', { name: 'Технический аудит' }).click()
    await expect(page.getByText('research confirmed').last()).toBeVisible()
    await page.getByRole('button', { name: 'Закрыть' }).click()

    // --- Research: взять в работу (ordered -> in_progress) ---
    await page.getByTestId('crud-search-input').fill(comment)
    const orderedRowAgain = page.locator('tbody tr').filter({ hasText: comment })
    await orderedRowAgain.first().click({ button: 'right' })
    await page.getByRole('menuitem', { name: /STR · Взять исследование в работу/ }).click()
    await expect(page.getByText('Исследования взяты в работу').last()).toBeVisible()

    await page.getByTestId('crud-search-input').fill(comment)
    const inProgressRow = page.locator('tbody tr').filter({ hasText: comment })
    await expect(inProgressRow.first().getByText('В работе')).toBeVisible()

    await inProgressRow.first().click({ button: 'right' })
    await page.getByRole('menuitem', { name: 'Просмотр' }).click()
    await page.getByRole('tab', { name: 'Технический аудит' }).click()
    await expect(page.getByText('research started').last()).toBeVisible()
    await page.getByRole('button', { name: 'Закрыть' }).click()

    // --- Tests: взять в работу (queued -> in_progress) ---
    // Tests has no `sample`/`research`-visible identifying text column (Research
    // has no `name`), so narrow the list by searching the research id (the
    // tests.research_id UUID column is part of the global search, cast to text
    // — see src/core/global_search.py) and pin the single fixture row by its
    // unique indicator name. (The /tests table also renders a structural empty
    // <tr>, so a raw row *count* is unreliable — hence the text filter.)
    await goToTests(page)
    await page.getByTestId('crud-search-input').fill(research.id)
    let testRow = page.locator('tbody tr').filter({ hasText: indicatorName })
    await expect(testRow.first().getByText('Запланировано')).toBeVisible()

    await testRow.first().click({ button: 'right' })
    await page.getByRole('menuitem', { name: /STR · Взять тест в работу/ }).click()
    await expect(page.getByText('Тесты взяты в работу').last()).toBeVisible()

    await page.getByTestId('crud-search-input').fill(research.id)
    testRow = page.locator('tbody tr').filter({ hasText: indicatorName })
    await expect(testRow.first().getByText('Выполняется')).toBeVisible()

    // --- Tests: внести результат (in_progress -> completed) ---
    await testRow.first().click({ button: 'right' })
    await page.getByRole('menuitem', { name: /RES · Внести результат теста/ }).click()
    await page.getByLabel('Значение').fill('12.5')
    await page.getByLabel('Норма').fill('<= 20')
    await page.getByRole('button', { name: 'Сохранить' }).click()
    await expect(page.getByText('Результаты тестов сохранены').last()).toBeVisible()

    await page.getByTestId('crud-search-input').fill(research.id)
    testRow = page.locator('tbody tr').filter({ hasText: indicatorName })
    await expect(testRow.first().getByText('Выполнено')).toBeVisible()

    // --- All tests terminal -> research auto-completes (server-side cascade) ---
    await goToResearch(page)
    await page.getByTestId('crud-search-input').fill(comment)
    const completedRow = page.locator('tbody tr').filter({ hasText: comment })
    await expect(completedRow.first().getByText('Завершено')).toBeVisible()

    await completedRow.first().click({ button: 'right' })
    await page.getByRole('menuitem', { name: 'Просмотр' }).click()
    await page.getByRole('tab', { name: 'Технический аудит' }).click()
    // research_completed has a dedicated Russian label (see
    // src/shared/ui/technical-audit.ts::actionLabel) instead of the generic
    // "action.replace(/[._-]/g, ' ')" fallback used for the other actions above.
    await expect(page.getByText('Исследование завершено').last()).toBeVisible()
    await page.getByRole('button', { name: 'Закрыть' }).click()

    await deleteIndicator(page.request, indicator.id)
    await deleteResearchGoal(page.request, goal.id)
  })

  test('tests: requeue returns an in-progress test to the queue, reject marks it rejected', async ({
    page
  }) => {
    await loginAsLabDoctor(page)
    const me = await currentUser(page.request)
    const sampleType = await firstReferenceItem(page.request, 'sample_types')
    const lab = await firstReferenceItem(page.request, 'labs')
    const { goal, indicator, indicatorName } = await createSingleIndicatorGoal(page.request, lab.id)

    const direction = await createDirection(page.request, {
      year_no: 2026,
      base_no: TEST_REQUEUE_REJECT_BASE_NO
    })
    const sample = await createSample(page.request, {
      name: 'LabDoctor requeue/reject sample',
      direction_id: direction.id,
      sample_type_id: sampleType.id
    })
    const assignResponse = await assignResearch(page.request, {
      sample_id: sample.id,
      actor_id: me.id,
      research_goal_id: goal.id
    })
    const research = (await assignResponse.json()).data as { id: string }
    // Setup only — register the sample and confirm/start research through the
    // API since this test's focus is the tests.requeue / tests.reject commands
    // (research.confirm/start are exercised through the UI in the previous
    // test). Registration is required so research.start moves the sample to
    // in_progress: rejecting the last test cascades the sample to `analyzed`
    // (reject_test also calls _complete_parents_when_terminal), which is only
    // valid from in_progress — from pending it 409s and rolls the reject back.
    await registerSample(page.request, sample.id, me.id, new Date().toISOString())
    await confirmResearch(page.request, research.id, me.id)
    await startResearch(page.request, research.id, me.id)

    await goToTests(page)
    // Narrow by research id, pin the row by its unique indicator name (see the
    // note in the previous test: the /tests table renders a structural empty
    // <tr>, so a raw row count is unreliable).
    await page.getByTestId('crud-search-input').fill(research.id)
    let testRow = page.locator('tbody tr').filter({ hasText: indicatorName })
    await expect(testRow.first().getByText('Запланировано')).toBeVisible()

    // --- взять в работу (queued -> in_progress) ---
    await testRow.first().click({ button: 'right' })
    await page.getByRole('menuitem', { name: /STR · Взять тест в работу/ }).click()
    await expect(page.getByText('Тесты взяты в работу').last()).toBeVisible()

    await page.getByTestId('crud-search-input').fill(research.id)
    testRow = page.locator('tbody tr').filter({ hasText: indicatorName })
    await expect(testRow.first().getByText('Выполняется')).toBeVisible()

    // --- вернуть в очередь (in_progress -> queued) ---
    await testRow.first().click({ button: 'right' })
    await page.getByRole('menuitem', { name: /REQ · Вернуть тест в очередь/ }).click()
    await expect(page.getByText('Тесты возвращены в очередь').last()).toBeVisible()

    await page.getByTestId('crud-search-input').fill(research.id)
    testRow = page.locator('tbody tr').filter({ hasText: indicatorName })
    await expect(testRow.first().getByText('Запланировано')).toBeVisible()

    // --- отклонить (queued -> rejected) ---
    await testRow.first().click({ button: 'right' })
    await page.getByRole('menuitem', { name: /REJ · Отклонить тест/ }).click()
    await page.getByLabel('Причина').fill('Показатель вне диапазона прибора')
    await page.getByRole('button', { name: 'Сохранить' }).click()
    await expect(page.getByText('Тесты отклонены').last()).toBeVisible()

    await page.getByTestId('crud-search-input').fill(research.id)
    testRow = page.locator('tbody tr').filter({ hasText: indicatorName })
    await expect(testRow.first().getByText('Отклонено')).toBeVisible()

    await deleteIndicator(page.request, indicator.id)
    await deleteResearchGoal(page.request, goal.id)
  })

  test('samples: reject (brak) shows in UI, fires an SSE notification in the bell, and is recorded in technical audit', async ({
    page
  }) => {
    // Login first so the direction/sample below are created under the doctor's
    // own session — Direction.created_by resolves the notification's
    // target_user_id (see resolve_notification_target in
    // src/contexts/laboratory_workflow/infrastructure/repositories.py), and
    // /dashboard (the post-login landing page) is what opens the SSE
    // connection (useSystemNotifications is only wired up in DashboardPage.vue).
    await loginAsLabDoctor(page)
    const direction = await createDirection(page.request, {
      year_no: 2026,
      base_no: SAMPLE_REJECT_BASE_NO
    })
    const sample = await createSample(page.request, {
      name: 'LabDoctor reject sample',
      direction_id: direction.id
    })
    const reason = `lab doctor brak check ${Date.now()}`

    await goToSamples(page)
    await page.getByTestId('crud-search-input').fill(sample.name)
    const row = page.locator('tbody tr').filter({ hasText: sample.name })
    await expect(row.first()).toBeVisible()

    await row.first().click({ button: 'right' })
    await page.getByRole('menuitem', { name: /REJ · Забраковать образец/ }).click()
    await page.getByLabel('Причина').fill(reason)
    await page.getByRole('button', { name: 'Сохранить' }).click()
    await expect(page.getByText('Образцы помечены как брак').last()).toBeVisible()

    await page.getByTestId('crud-search-input').fill(sample.name)
    const rejectedRow = page.locator('tbody tr').filter({ hasText: sample.name })
    await expect(rejectedRow.first().getByText('Брак')).toBeVisible()

    // --- SSE notification: the reject above should have pushed a
    // `notification.created` event onto the already-open EventSource and
    // shown up in the bell/slideover. ---
    await goToDashboard(page)
    await page.locator('[data-tour="dashboard-notifications"]').click()
    await expect(page.getByRole('heading', { name: 'Notifications' })).toBeVisible()

    const notification = page.getByText(reason, { exact: false }).last()
    await expect(notification).toBeVisible({ timeout: 15_000 })

    const notificationRow = page.locator('div').filter({ hasText: reason }).last()
    await notificationRow.getByRole('button', { name: 'Mark as read' }).click()
    await page.getByRole('tab', { name: /Read/ }).click()
    await expect(page.getByText(reason).last()).toBeVisible()
    await page.keyboard.press('Escape')

    // --- Technical audit ---
    await goToSamples(page)
    await page.getByTestId('crud-search-input').fill(sample.name)
    const auditRow = page.locator('tbody tr').filter({ hasText: sample.name })
    await auditRow.first().click({ button: 'right' })
    await page.getByRole('menuitem', { name: /Просмотр/ }).click()
    await page.getByRole('tab', { name: 'Технический аудит' }).click()
    await expect(page.getByText('sample rejected').last()).toBeVisible()
  })

  test('research: reject (draft -> rejected) reflects in UI and technical audit', async ({ page }) => {
    await loginAsLabDoctor(page)
    const me = await currentUser(page.request)
    const researchGoal = await firstReferenceItem(page.request, 'research_goals')

    const direction = await createDirection(page.request, {
      year_no: 2026,
      base_no: RESEARCH_REJECT_BASE_NO
    })
    const sample = await createSample(page.request, {
      name: 'LabDoctor research reject sample',
      direction_id: direction.id
    })
    const comment = `E2E lab doctor reject research ${Date.now()}`
    const assignResponse = await assignResearch(page.request, {
      sample_id: sample.id,
      actor_id: me.id,
      research_goal_id: researchGoal.id,
      comment
    })
    expect(assignResponse.ok()).toBeTruthy()
    const research = (await assignResponse.json()).data as { id: string }

    await goToResearch(page)
    await page.getByTestId('crud-search-input').fill(comment)
    const row = page.locator('tbody tr').filter({ hasText: comment })
    await expect(row.first()).toBeVisible()
    await expect(row.first().getByText('Черновик')).toBeVisible()

    await row.first().click({ button: 'right' })
    await page.getByRole('menuitem', { name: /REJ · Отклонить исследование/ }).click()
    await page.getByLabel('Причина').fill('Образец не соответствует цели исследования')
    await page.getByRole('button', { name: 'Сохранить' }).click()
    await expect(page.getByText('Исследования отклонены').last()).toBeVisible()

    // reject_research overwrites research.comment with the reason (see
    // repositories.py::reject_research: `research.comment = reason or ...`),
    // so the original `comment` no longer matches the row — search by the
    // stable research id (UUID column, part of the global search) instead.
    await page.getByTestId('crud-search-input').fill(research.id)
    const rejectedRow = page.locator('tbody tr')
    await expect(rejectedRow).toHaveCount(1)
    await expect(rejectedRow.first().getByText('Отклонено')).toBeVisible()

    await rejectedRow.first().click({ button: 'right' })
    await page.getByRole('menuitem', { name: 'Просмотр' }).click()
    await page.getByRole('tab', { name: 'Технический аудит' }).click()
    await expect(page.getByText('research rejected').last()).toBeVisible()
  })

  test('dashboard: shows the KPI stat cards and the workflow chart', async ({ page }) => {
    // NOTE: the dashboard is not role-scoped today (src/infrastructure/
    // repositories/dashboard.py::_kpis returns the same fixed 6-card set for
    // every role — there is no "own_lab"-filtered "waiting for confirmation"
    // metric). Documented as a known limitation in
    // docs/flows/lab-doctor.flow.md rather than invented here.
    await loginAsLabDoctor(page)

    // Scope the KPI-label assertions to the stats card block — some labels
    // (e.g. "Брак") also render as status badges elsewhere on the dashboard
    // (samples-by-status), which would break an unscoped exact-text match.
    const stats = page.locator('[data-tour="dashboard-stats"]')
    await expect(stats).toBeVisible()
    for (const label of [
      'Поступило образцов',
      'Выполнено тестов',
      'Просрочено',
      'Среднее время',
      'Брак',
      'Исследования в работе'
    ]) {
      await expect(stats.getByText(label, { exact: true })).toBeVisible()
    }

    await expect(page.locator('[data-tour="dashboard-chart"]')).toBeVisible()
  })
})
