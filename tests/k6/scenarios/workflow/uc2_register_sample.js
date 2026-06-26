// UC2 — Register sample (guardrails)
// Story 1: A clerk registers an incoming sample with a received timestamp.
//
// Covers:
//   UC2 — POST /samples/{id}/register unknown sample → 404 (UoW rolls back)
//   AC: missing actor_id/received_at → 422
//   AC: naive (timezone-less) received_at → 422 (schema validator)
//
// Run: k6 run tests/k6/scenarios/workflow/uc2_register_sample.js

import { check } from 'k6';
import http from '../../helper/http.js';
import { ACTOR_ID, BASE, JSON_HEADERS, unknownId } from './_shared.js';

export const options = {
  scenarios: {
    uc2: {
      executor: 'shared-iterations', exec: 'run', vus: 1, iterations: 1,
      tags: { context: 'workflow', uc: 'UC2', title: 'Register sample', story: 'Story 1', actor: 'staff' },
    },
  },
  thresholds: {
    http_req_duration: [{ threshold: 'p(95)<2000' }],
  },
};

export function run() {
  const id = unknownId();
  const receivedAt = new Date().toISOString();

  const notFound = http.post(
    `${BASE}/samples/${id}/register`,
    JSON.stringify({ actor_id: ACTOR_ID, received_at: receivedAt }),
    { headers: JSON_HEADERS, expectedStatus: 404 },
  );
  check(notFound, { 'UC2 POST /samples/{id}/register → 404': (r) => r.status === 404 });

  const missing = http.post(
    `${BASE}/samples/${id}/register`,
    JSON.stringify({ actor_id: ACTOR_ID }),
    { headers: JSON_HEADERS, expectedStatus: 422 },
  );
  check(missing, { 'UC2 POST /samples/{id}/register → 422': (r) => r.status === 422 });

  const naive = http.post(
    `${BASE}/samples/${id}/register`,
    JSON.stringify({ actor_id: ACTOR_ID, received_at: '2026-06-26T10:00:00' }),
    { headers: JSON_HEADERS, expectedStatus: 422 },
  );
  check(naive, { 'UC2 naive received_at → 422': (r) => r.status === 422 });
}
