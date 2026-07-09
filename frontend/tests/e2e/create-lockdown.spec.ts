import { test, expect } from './support/fixtures'
import { API_BASE } from './support/api'

const NIL_UUID = '00000000-0000-0000-0000-000000000000'

// The workflow refactor removed the generic POST create routes for samples,
// research and tests: samples are only added nested under a draft direction
// (POST /directions/{id}/samples) or via import, and research/tests are created
// solely through the assign-research command. This spec pins the API contract
// down; the UI-level proof of the new creation paths lives in the import spec
// (single /directions/import endpoint) and direction-lifecycle spec (nested
// "add sample to direction" from a draft direction card).
test.describe('direct create lockdown (workflow refactor)', () => {
  test('generic POST create is forbidden for samples, research and tests', async ({ request }) => {
    const sample = await request.post(`${API_BASE}/samples`, {
      data: { name: 'must be rejected' }
    })
    expect(sample.status()).toBe(405)

    const research = await request.post(`${API_BASE}/research`, {
      data: { sample_id: NIL_UUID, research_goal_id: NIL_UUID }
    })
    expect(research.status()).toBe(405)

    const testCreate = await request.post(`${API_BASE}/tests`, {
      data: { research_id: NIL_UUID }
    })
    expect(testCreate.status()).toBe(405)
  })
})
