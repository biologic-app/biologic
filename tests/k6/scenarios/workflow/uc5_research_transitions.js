// UC5 — Research transitions (guardrails)
// Story 2: Research moves draft → ordered → in_progress (or rejected). Each
// transition is a command on the single Unit of Work.
//
// Covers:
//   UC5 — POST /research/{id}/confirm unknown → 404
//   UC5 — POST /research/{id}/start   unknown → 404
//   UC5 — POST /research/{id}/reject  unknown → 404
//   AC: reject without reason → 422
//
// Run: k6 run tests/k6/scenarios/workflow/uc5_research_transitions.js

import { check } from 'k6';
import http from '../../helper/http.js';
import { ACTOR_ID, BASE, JSON_HEADERS, unknownId } from './_shared.js';

export const options = {
  scenarios: {
    uc5: {
      executor: 'shared-iterations', exec: 'run', vus: 1, iterations: 1,
      tags: { context: 'workflow', uc: 'UC5', title: 'Research transitions', story: 'Story 2', actor: 'staff' },
    },
  },
  thresholds: {
    http_req_duration: [{ threshold: 'p(95)<2000' }],
  },
};

export function run() {
  const id = unknownId();
  const actor = JSON.stringify({ actor_id: ACTOR_ID });

  const confirm = http.post(`${BASE}/research/${id}/confirm`, actor, { headers: JSON_HEADERS, expectedStatus: 404 });
  check(confirm, { 'UC5 POST /research/{id}/confirm → 404': (r) => r.status === 404 });

  const start = http.post(`${BASE}/research/${id}/start`, actor, { headers: JSON_HEADERS, expectedStatus: 404 });
  check(start, { 'UC5 POST /research/{id}/start → 404': (r) => r.status === 404 });

  const reject = http.post(
    `${BASE}/research/${id}/reject`,
    JSON.stringify({ actor_id: ACTOR_ID, reason: 'Out of scope' }),
    { headers: JSON_HEADERS, expectedStatus: 404 },
  );
  check(reject, { 'UC5 POST /research/{id}/reject → 404': (r) => r.status === 404 });

  const noReason = http.post(`${BASE}/research/${id}/reject`, actor, { headers: JSON_HEADERS, expectedStatus: 422 });
  check(noReason, { 'UC5 reject without reason → 422': (r) => r.status === 422 });
}
