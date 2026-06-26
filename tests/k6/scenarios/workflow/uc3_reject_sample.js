// UC3 — Reject sample (guardrails)
// Story 1: A clerk rejects an unusable sample with a reason. Rejection cascades
// to child research/tests inside ONE Unit of Work — all-or-nothing.
//
// Covers:
//   UC3 — POST /samples/{id}/reject unknown sample → 404 (nothing persisted)
//   AC: missing reason → 422
//
// Run: k6 run tests/k6/scenarios/workflow/uc3_reject_sample.js

import { check } from 'k6';
import http from '../../helper/http.js';
import { ACTOR_ID, BASE, JSON_HEADERS, unknownId } from './_shared.js';

export const options = {
  scenarios: {
    uc3: {
      executor: 'shared-iterations', exec: 'run', vus: 1, iterations: 1,
      tags: { context: 'workflow', uc: 'UC3', title: 'Reject sample', story: 'Story 1', actor: 'staff' },
    },
  },
  thresholds: {
    http_req_duration: [{ threshold: 'p(95)<2000' }],
  },
};

export function run() {
  const id = unknownId();

  const notFound = http.post(
    `${BASE}/samples/${id}/reject`,
    JSON.stringify({ actor_id: ACTOR_ID, reason: 'Container damaged' }),
    { headers: JSON_HEADERS, expectedStatus: 404 },
  );
  check(notFound, { 'UC3 POST /samples/{id}/reject → 404': (r) => r.status === 404 });

  const missing = http.post(
    `${BASE}/samples/${id}/reject`,
    JSON.stringify({ actor_id: ACTOR_ID }),
    { headers: JSON_HEADERS, expectedStatus: 422 },
  );
  check(missing, { 'UC3 POST /samples/{id}/reject → 422': (r) => r.status === 422 });
}
