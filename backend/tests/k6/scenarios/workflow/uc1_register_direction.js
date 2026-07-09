// UC1 — Register direction (guardrails)
// Story 1: A lab clerk registers a direction. Registration is a lifecycle
// command routed through the single Unit of Work; this UC asserts its
// contract guardrails.
//
// Covers:
//   UC1 — POST /directions/{id}/register unknown direction → 404 (rolls back)
//   AC: missing actor_id → 422 (rejected before the UoW opens)
//
// Run: k6 run tests/k6/scenarios/workflow/uc1_register_direction.js

import { check } from 'k6';
import http from '../../helper/http.js';
import { ACTOR_ID, BASE, JSON_HEADERS, unknownId } from './_shared.js';

export const options = {
  scenarios: {
    uc1: {
      executor: 'shared-iterations', exec: 'run', vus: 1, iterations: 1,
      tags: { context: 'workflow', uc: 'UC1', title: 'Register direction', story: 'Story 1', actor: 'staff' },
    },
  },
  thresholds: {
    http_req_duration: [{ threshold: 'p(95)<2000' }],
  },
};

export function run() {
  const id = unknownId();

  const notFound = http.post(
    `${BASE}/directions/${id}/register`,
    JSON.stringify({ actor_id: ACTOR_ID, comment: 'k6 contract probe' }),
    { headers: JSON_HEADERS, expectedStatus: 404 },
  );
  check(notFound, { 'UC1 POST /directions/{id}/register → 404': (r) => r.status === 404 });

  const invalid = http.post(
    `${BASE}/directions/${id}/register`,
    JSON.stringify({ comment: 'no actor' }),
    { headers: JSON_HEADERS, expectedStatus: 422 },
  );
  check(invalid, { 'UC1 POST /directions/{id}/register → 422': (r) => r.status === 422 });
}
