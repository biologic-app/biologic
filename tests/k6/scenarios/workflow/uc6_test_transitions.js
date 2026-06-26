// UC6 — Test transitions (guardrails)
// Story 3: A test moves queued → in_progress → completed (or requeued /
// rejected). Completing a test may cascade research/sample completion, all in
// ONE Unit of Work.
//
// Covers:
//   UC6 — POST /tests/{id}/start    unknown → 404
//   UC6 — POST /tests/{id}/complete unknown → 404
//   UC6 — POST /tests/{id}/requeue  unknown → 404
//   UC6 — POST /tests/{id}/reject   unknown → 404
//   AC: complete without value → 422
//
// Run: k6 run tests/k6/scenarios/workflow/uc6_test_transitions.js

import { check } from 'k6';
import http from '../../helper/http.js';
import { ACTOR_ID, BASE, JSON_HEADERS, unknownId } from './_shared.js';

export const options = {
  scenarios: {
    uc6: {
      executor: 'shared-iterations', exec: 'run', vus: 1, iterations: 1,
      tags: { context: 'workflow', uc: 'UC6', title: 'Test transitions', story: 'Story 3', actor: 'staff' },
    },
  },
  thresholds: {
    http_req_duration: [{ threshold: 'p(95)<2000' }],
  },
};

export function run() {
  const id = unknownId();
  const actor = JSON.stringify({ actor_id: ACTOR_ID });

  const start = http.post(`${BASE}/tests/${id}/start`, actor, { headers: JSON_HEADERS, expectedStatus: 404 });
  check(start, { 'UC6 POST /tests/{id}/start → 404': (r) => r.status === 404 });

  const complete = http.post(
    `${BASE}/tests/${id}/complete`,
    JSON.stringify({ actor_id: ACTOR_ID, value: '7.4' }),
    { headers: JSON_HEADERS, expectedStatus: 404 },
  );
  check(complete, { 'UC6 POST /tests/{id}/complete → 404': (r) => r.status === 404 });

  const requeue = http.post(`${BASE}/tests/${id}/requeue`, actor, { headers: JSON_HEADERS, expectedStatus: 404 });
  check(requeue, { 'UC6 POST /tests/{id}/requeue → 404': (r) => r.status === 404 });

  const reject = http.post(
    `${BASE}/tests/${id}/reject`,
    JSON.stringify({ actor_id: ACTOR_ID, reason: 'Instrument fault' }),
    { headers: JSON_HEADERS, expectedStatus: 404 },
  );
  check(reject, { 'UC6 POST /tests/{id}/reject → 404': (r) => r.status === 404 });

  const noValue = http.post(`${BASE}/tests/${id}/complete`, actor, { headers: JSON_HEADERS, expectedStatus: 422 });
  check(noValue, { 'UC6 complete without value → 422': (r) => r.status === 422 });
}
