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
  const response = await request.post(`${API_BASE}/samples`, { data: payload })
  const body = await response.json()
  return body.data as { id: string; status_id: string; name: string; direction_id: string }
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
  return body.items as Array<{ id: string; name: string }>
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

/** Removes any leftover e2e fixture directions (and their samples) for a base_no, so import tests are re-runnable. */
export async function cleanupDirectionsByBaseNo(request: APIRequestContext, baseNo: number) {
  const directions = await findDirectionsByBaseNo(request, baseNo)
  for (const direction of directions) {
    const samples = await findSamplesByDirection(request, direction.id)
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
