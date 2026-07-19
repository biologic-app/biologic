import type { APIRequestContext } from '@playwright/test'

export const API_BASE = process.env.E2E_API_BASE_URL || 'http://localhost:8080/api/v1'

export async function currentUser(request: APIRequestContext) {
  const response = await request.get(`${API_BASE}/auth/me`)
  const body = await response.json()
  return body.data.user as { id: string; username: string; role_key: string }
}

export async function createDirection(
  request: APIRequestContext,
  payload: Record<string, unknown>
) {
  const response = await request.post(`${API_BASE}/directions`, { data: payload })
  const body = await response.json()
  return body.data as { id: string; status_id: string; base_no: number; year_no: number }
}

export async function createSample(request: APIRequestContext, payload: Record<string, unknown>) {
  // Direct POST /samples is forbidden after the workflow refactor — a sample is
  // created nested under its (draft) direction, and direction_id travels in the
  // path rather than the body.
  const { direction_id, ...body } = payload as { direction_id?: string } & Record<string, unknown>
  const response = await request.post(`${API_BASE}/directions/${direction_id}/samples`, {
    data: body
  })
  const parsed = await response.json()
  return parsed.data as { id: string; status_id: string; name: string; direction_id: string }
}

export async function assignResearch(
  request: APIRequestContext,
  payload: { sample_id: string; actor_id: string; research_goal_id: string; comment?: string }
) {
  const response = await request.post(`${API_BASE}/samples/${payload.sample_id}/assign-research`, {
    data: payload
  })
  return response
}

export async function registerDirection(
  request: APIRequestContext,
  directionId: string,
  actorId: string
) {
  return request.post(`${API_BASE}/directions/${directionId}/register`, {
    data: { actor_id: actorId }
  })
}

export async function findDirectionsByBaseNo(request: APIRequestContext, baseNo: number) {
  const response = await request.get(`${API_BASE}/directions`, {
    params: { filters: JSON.stringify({ base_no: baseNo }), limit: 50 }
  })
  const body = await response.json()
  return body.items as Array<{ id: string }>
}

export async function findSamplesByDirection(request: APIRequestContext, directionId: string) {
  const response = await request.get(`${API_BASE}/samples`, {
    params: { filters: JSON.stringify({ direction_id: directionId }), limit: 200 }
  })
  const body = await response.json()
  return body.items as Array<{ id: string; name: string; protocol_id: string | null }>
}

export async function deleteProtocol(request: APIRequestContext, protocolId: string) {
  await request.delete(`${API_BASE}/protocols/${protocolId}`).catch(() => undefined)
}

export async function updateSample(
  request: APIRequestContext,
  sampleId: string,
  payload: Record<string, unknown>
) {
  const response = await request.patch(`${API_BASE}/samples/${sampleId}`, { data: payload })
  const body = await response.json()
  return body.data
}

export async function firstReferenceItem(request: APIRequestContext, resource: string) {
  const response = await request.get(`${API_BASE}/${resource}`, { params: { limit: 1 } })
  const body = await response.json()
  return body.items[0] as { id: string; name: string }
}

export async function deleteDirection(request: APIRequestContext, directionId: string) {
  await request.delete(`${API_BASE}/directions/${directionId}`).catch(() => undefined)
}

export async function deleteSample(request: APIRequestContext, sampleId: string) {
  await request.delete(`${API_BASE}/samples/${sampleId}`).catch(() => undefined)
}

/** Removes any leftover e2e fixture directions (and their samples/protocols) for a base_no, so tests are re-runnable. */
export async function cleanupDirectionsByBaseNo(request: APIRequestContext, baseNo: number) {
  const directions = await findDirectionsByBaseNo(request, baseNo)
  for (const direction of directions) {
    const samples = await findSamplesByDirection(request, direction.id)
    const protocolIds = new Set(samples.map((sample) => sample.protocol_id).filter(Boolean))
    for (const protocolId of protocolIds) {
      await deleteProtocol(request, protocolId as string)
    }
    for (const sample of samples) {
      await deleteSample(request, sample.id)
    }
    await deleteDirection(request, direction.id)
  }
}

export async function rejectSample(
  request: APIRequestContext,
  sampleId: string,
  actorId: string,
  reason: string
) {
  return request.post(`${API_BASE}/samples/${sampleId}/reject`, {
    data: { actor_id: actorId, reason }
  })
}

export async function registerSample(
  request: APIRequestContext,
  sampleId: string,
  actorId: string,
  receivedAt: string
) {
  return request.post(`${API_BASE}/samples/${sampleId}/register`, {
    data: { actor_id: actorId, received_at: receivedAt }
  })
}

export async function findTestsByResearch(request: APIRequestContext, researchId: string) {
  const response = await request.get(`${API_BASE}/tests`, {
    params: { filters: JSON.stringify({ research_id: researchId }), limit: 200 }
  })
  const body = await response.json()
  return body.items as Array<{ id: string }>
}

export async function completeTest(
  request: APIRequestContext,
  testId: string,
  actorId: string,
  value: string
) {
  return request.post(`${API_BASE}/tests/${testId}/complete`, {
    data: { actor_id: actorId, value, norm: 'N/A' }
  })
}

export async function closeSample(
  request: APIRequestContext,
  sampleId: string,
  actorId: string,
  verdict: string
) {
  return request.post(`${API_BASE}/samples/${sampleId}/close`, {
    data: { actor_id: actorId, verdict }
  })
}

export async function rejectResearch(
  request: APIRequestContext,
  researchId: string,
  actorId: string,
  reason: string
) {
  return request.post(`${API_BASE}/research/${researchId}/reject`, {
    data: { actor_id: actorId, reason }
  })
}

export async function rejectTest(
  request: APIRequestContext,
  testId: string,
  actorId: string,
  reason: string
) {
  return request.post(`${API_BASE}/tests/${testId}/reject`, { data: { actor_id: actorId, reason } })
}

/** Creates a dedicated research_goal reference-data row for a fixture — used
 * instead of `firstReferenceItem(request, 'research_goals')` when the test
 * needs to control exactly how many indicators (and therefore how many
 * `tests` rows) the goal produces on `assign-research`. */
export async function createResearchGoal(
  request: APIRequestContext,
  payload: Record<string, unknown>
) {
  const response = await request.post(`${API_BASE}/research_goals`, { data: payload })
  const body = await response.json()
  return body.data as { id: string; code: string; name: string }
}

export async function createIndicator(request: APIRequestContext, payload: Record<string, unknown>) {
  const response = await request.post(`${API_BASE}/indicators`, { data: payload })
  const body = await response.json()
  return body.data as { id: string; name: string }
}

export async function deleteResearchGoal(request: APIRequestContext, researchGoalId: string) {
  await request.delete(`${API_BASE}/research_goals/${researchGoalId}`).catch(() => undefined)
}

export async function deleteIndicator(request: APIRequestContext, indicatorId: string) {
  await request.delete(`${API_BASE}/indicators/${indicatorId}`).catch(() => undefined)
}

/** Drives a freshly-created sample all the way to `completed`, via the same
 * command sequence a lab technician would run — used to set up protocol
 * e2e fixtures without re-testing the research/tests workflow itself.
 *
 * New (simplified) status model: `assign-research` creates the research and
 * its tests directly in `in_progress` (no confirm/start/queue steps). The
 * sample is registered so the "work started" side effect on the first test
 * complete (`registered -> in_progress`) has a valid source status; once every
 * test is terminal the server cascades the research to `completed` and the
 * sample to `analyzed`, from where `close_sample` moves it to `completed`. */
export async function advanceSampleToCompleted(
  request: APIRequestContext,
  params: { sampleId: string; actorId: string; researchGoalId: string }
) {
  const assignResponse = await assignResearch(request, {
    sample_id: params.sampleId,
    actor_id: params.actorId,
    research_goal_id: params.researchGoalId
  })
  const research = (await assignResponse.json()).data as { id: string }

  // Register the sample first: completing the first test starts the sample
  // (registered -> in_progress), and finishing the last test then cascades
  // it in_progress -> analyzed. Completing a test on a still-pending sample
  // would try pending -> analyzed and 409 (invalid transition), rolling the
  // whole command back.
  await registerSample(request, params.sampleId, params.actorId, new Date().toISOString())

  const tests = await findTestsByResearch(request, research.id)
  for (const test of tests) {
    await completeTest(request, test.id, params.actorId, 'OK')
  }

  await closeSample(request, params.sampleId, params.actorId, 'Соответствует требованиям')
}
