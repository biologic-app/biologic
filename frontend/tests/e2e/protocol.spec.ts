import { test, expect } from './support/fixtures'
import { loginAsRegistrar, loginAsSanitaryInspector } from './support/auth'
import { closeEntityModal, goToProtocols, goToSamples } from './support/nav'
import {
  API_BASE,
  advanceSampleToCompleted,
  cleanupDirectionsByBaseNo,
  createDirection,
  createSample,
  currentUser,
  firstReferenceItem
} from './support/api'

// Registrar creates a lab protocol from completed samples of one direction
// (docs/flows/registrator.flow.md §16); sanitary inspector can view it
// read-only afterwards (docs/flows/sanitary-doctor.flow.md §5).
const PROTOCOL_BASE_NO = 900501

test.describe('protocol creation and viewing', () => {
  test.beforeEach(async ({ request }) => {
    await cleanupDirectionsByBaseNo(request, PROTOCOL_BASE_NO)
  })

  test('registrar creates a protocol for completed samples of one direction', async ({
    page,
    request
  }) => {
    await loginAsRegistrar(page)
    const me = await currentUser(page.request)
    const sampleType = await firstReferenceItem(page.request, 'sample_types')
    const researchGoal = await firstReferenceItem(page.request, 'research_goals')

    const direction = await createDirection(page.request, {
      year_no: 2026,
      base_no: PROTOCOL_BASE_NO
    })
    const sampleA = await createSample(page.request, {
      name: 'Protocol demo sample A',
      direction_id: direction.id,
      sample_type_id: sampleType.id
    })
    const sampleB = await createSample(page.request, {
      name: 'Protocol demo sample B',
      direction_id: direction.id,
      sample_type_id: sampleType.id
    })

    for (const sample of [sampleA, sampleB]) {
      await advanceSampleToCompleted(request, {
        sampleId: sample.id,
        actorId: me.id,
        researchGoalId: researchGoal.id
      })
    }

    await goToSamples(page)
    await page.getByTestId('crud-search-input').fill('Protocol demo sample')
    await expect(page.locator('tbody tr').filter({ hasText: 'Protocol demo sample A' })).toBeVisible()
    await expect(page.locator('tbody tr').filter({ hasText: 'Protocol demo sample B' })).toBeVisible()

    await page.locator('thead').getByRole('checkbox').first().click()
    await expect(page.getByText('2 выбрано')).toBeVisible()

    const createProtocolButton = page.getByTestId('create-protocol-from-selection')
    await expect(createProtocolButton).toBeEnabled()
    await createProtocolButton.click()
    await expect(page.getByText('Создать протокол (2 образцов)')).toBeVisible()
    await page.getByRole('button', { name: 'Сохранить' }).click()
    await expect(page.getByText('Протокол создан').last()).toBeVisible()

    // Both samples now carry a protocol_id — re-selecting them for a second
    // protocol must be blocked (a sample belongs to at most one protocol).
    await page.getByTestId('crud-search-input').fill('Protocol demo sample')
    await page.locator('thead').getByRole('checkbox').first().click()
    await expect(createProtocolButton).toBeDisabled()

    await goToProtocols(page)
    const protocolRow = page.locator('tbody tr').filter({ hasText: '2026' }).first()
    await expect(protocolRow).toBeVisible()
    await protocolRow.click({ button: 'right' })
    await page.getByRole('menuitem', { name: 'Просмотр', exact: true }).click()
    await expect(page.getByRole('tab', { name: 'Карточка' })).toBeVisible()
    await expect(page.getByText('Создано')).toBeVisible()

    // Protocols keep the generic "Связанные" tab label (only directions/samples/
    // research get an entity-specific one after the modal rework); its body is a
    // table of the linked sample rows rather than an "N записей" summary line.
    await page.getByRole('tab', { name: 'Связанные' }).click()
    await expect(page.getByText('Protocol demo sample A')).toBeVisible()
    await expect(page.getByText('Protocol demo sample B')).toBeVisible()
  })

  test('sanitary inspector can view (but not create) the protocol the registrar made', async ({
    page,
    request
  }) => {
    await loginAsRegistrar(page)
    const me = await currentUser(page.request)
    const sampleType = await firstReferenceItem(page.request, 'sample_types')
    const researchGoal = await firstReferenceItem(page.request, 'research_goals')

    const direction = await createDirection(page.request, {
      year_no: 2026,
      base_no: PROTOCOL_BASE_NO
    })
    const sample = await createSample(page.request, {
      name: 'SanInspector protocol view sample',
      direction_id: direction.id,
      sample_type_id: sampleType.id
    })
    await advanceSampleToCompleted(request, {
      sampleId: sample.id,
      actorId: me.id,
      researchGoalId: researchGoal.id
    })
    const protocolResponse = await request.post(`${API_BASE}/protocols`, {
      data: { actor_id: me.id, sample_ids: [sample.id] }
    })
    expect(protocolResponse.ok()).toBeTruthy()

    await loginAsSanitaryInspector(page)
    await goToProtocols(page)
    await expect(page.getByRole('button', { name: 'Создать' })).toHaveCount(0)

    const protocolRow = page.locator('tbody tr').filter({ hasText: '2026' }).first()
    await expect(protocolRow).toBeVisible()
    await protocolRow.click({ button: 'right' })
    await expect(page.getByRole('menuitem', { name: 'Просмотр', exact: true })).toBeEnabled()
    await expect(page.getByRole('menuitem', { name: 'Редактировать' })).toBeDisabled()
    await page.getByRole('menuitem', { name: 'Просмотр', exact: true }).click()

    await expect(page.getByRole('button', { name: 'Редактировать' })).toHaveCount(0)
    await page.getByRole('tab', { name: 'Связанные' }).click()
    await expect(page.getByText('SanInspector protocol view sample')).toBeVisible()

    await closeEntityModal(page)
    await goToSamples(page)
    await expect(page.getByTestId('create-protocol-from-selection')).toHaveCount(0)
  })
})
