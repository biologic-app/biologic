import type { APIRequestContext } from '@playwright/test'
import { test, expect } from './support/fixtures'
import { loginAsLabDoctor } from './support/auth'
import { closeEntityModal, goToDashboard, goToResearch, goToSamples, goToTests } from './support/nav'
import {
  assignResearch,
  cleanupDirectionsByBaseNo,
  createDirection,
  createIndicator,
  createResearchGoal,
  createSample,
  currentUser,
  deleteIndicator,
  deleteResearchGoal,
  firstReferenceItem,
  registerSample
} from './support/api'

// Full lifecycle for the lab doctor (ВЛ, role_key=lab_doctor, account
// doctor/doctor123) per docs/flows/lab-doctor.flow.md under the SIMPLIFIED
// status model: research and tests are created directly in `in_progress`
// (no confirm/start/queue commands). The lab doctor enters a test result
// (tests.complete) which — as the last terminal test — cascades the research
// to `completed` and the sample to `analyzed`; plus tests.reject,
// research.reject, samples.reject (with the SSE notification it fires) and
// the shared dashboard. Base_no ranges are unique per test for isolation,
// matching direction-lifecycle.spec.ts / sample-lifecycle.spec.ts.
const RESEARCH_TESTS_BASE_NO = 930101
const TEST_REJECT_BASE_NO = 930102
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
      TEST_REJECT_BASE_NO,
      SAMPLE_REJECT_BASE_NO,
      RESEARCH_REJECT_BASE_NO
    ]) {
      await cleanupDirectionsByBaseNo(request, baseNo)
    }
  })

  test('research starts in_progress; entering a test result completes the test and auto-completes the research', async ({
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
    // assign-research creates the research (and its single test) directly in
    // `in_progress` — there is no longer a draft/ordered stage nor a
    // confirm/start command.
    const assignResponse = await assignResearch(page.request, {
      sample_id: sample.id,
      actor_id: me.id,
      research_goal_id: goal.id,
      comment
    })
    expect(assignResponse.ok()).toBeTruthy()
    const research = (await assignResponse.json()).data as { id: string }
    // Register the sample (pending -> registered) so completing the test moves
    // it to in_progress (the "work started" side effect, formerly on
    // research.start, now on the first test complete/reject); the last test
    // then cascades the sample in_progress -> analyzed. Completing a test on a
    // still-pending sample would attempt pending -> analyzed and 409.
    await registerSample(page.request, sample.id, me.id, new Date().toISOString())

    // --- Research is already in_progress ("В работе") — no confirm/start ---
    await goToResearch(page)
    await page.getByTestId('crud-search-input').fill(comment)
    const researchRow = page.locator('tbody tr').filter({ hasText: comment })
    await expect(researchRow.first()).toBeVisible()
    await expect(researchRow.first().getByText('В работе')).toBeVisible()

    await researchRow.first().click({ button: 'right' })
    await page.getByRole('menuitem', { name: 'Просмотр' }).click()
    await expect(page.getByText('В работе').first()).toBeVisible()
    await page.getByTestId('entity-detail-technical-tab').click()
    // research_assigned has a dedicated Russian label (see
    // src/shared/ui/technical-audit.ts::actionLabel).
    await expect(page.getByText('Исследование назначено').last()).toBeVisible()
    await closeEntityModal(page)

    // --- Tests: the single test is already in_progress ("Выполняется") ---
    // Tests has no `sample`/`research`-visible identifying text column (Research
    // has no `name`), so narrow the list by searching the research id (the
    // tests.research_id UUID column is part of the global search, cast to text
    // — see src/core/global_search.py) and pin the single fixture row by its
    // unique indicator name. (The /tests table also renders a structural empty
    // <tr>, so a raw row *count* is unreliable — hence the text filter.)
    await goToTests(page)
    await page.getByTestId('crud-search-input').fill(research.id)
    let testRow = page.locator('tbody tr').filter({ hasText: indicatorName })
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
    await page.getByTestId('entity-detail-technical-tab').click()
    // research_completed has a dedicated Russian label (see
    // src/shared/ui/technical-audit.ts::actionLabel).
    await expect(page.getByText('Исследование завершено').last()).toBeVisible()
    await closeEntityModal(page)

    await deleteIndicator(page.request, indicator.id)
    await deleteResearchGoal(page.request, goal.id)
  })

  test('tests: reject marks an in-progress test rejected', async ({ page }) => {
    await loginAsLabDoctor(page)
    const me = await currentUser(page.request)
    const sampleType = await firstReferenceItem(page.request, 'sample_types')
    const lab = await firstReferenceItem(page.request, 'labs')
    const { goal, indicator, indicatorName } = await createSingleIndicatorGoal(page.request, lab.id)

    const direction = await createDirection(page.request, {
      year_no: 2026,
      base_no: TEST_REJECT_BASE_NO
    })
    const sample = await createSample(page.request, {
      name: 'LabDoctor reject-test sample',
      direction_id: direction.id,
      sample_type_id: sampleType.id
    })
    const assignResponse = await assignResearch(page.request, {
      sample_id: sample.id,
      actor_id: me.id,
      research_goal_id: goal.id
    })
    const research = (await assignResponse.json()).data as { id: string }
    // Register the sample so rejecting the (only) test can start it and then
    // cascade in_progress -> analyzed (reject_test also runs the
    // "complete parents when terminal" cascade); from pending it would 409.
    await registerSample(page.request, sample.id, me.id, new Date().toISOString())

    await goToTests(page)
    // Narrow by research id, pin the row by its unique indicator name (see the
    // note in the previous test: the /tests table renders a structural empty
    // <tr>, so a raw row count is unreliable).
    await page.getByTestId('crud-search-input').fill(research.id)
    let testRow = page.locator('tbody tr').filter({ hasText: indicatorName })
    // The test is created directly in_progress ("Выполняется") — no queue/start.
    await expect(testRow.first().getByText('Выполняется')).toBeVisible()

    // --- отклонить (in_progress -> rejected) ---
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
    await page.getByTestId('entity-detail-technical-tab').click()
    await expect(page.getByText('sample rejected').last()).toBeVisible()
  })

  test('research: reject (in_progress -> rejected) reflects in UI and technical audit', async ({
    page
  }) => {
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
    // Research is created directly in_progress ("В работе") — no draft stage.
    await expect(row.first().getByText('В работе')).toBeVisible()

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
    await page.getByTestId('entity-detail-technical-tab').click()
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
