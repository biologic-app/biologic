// UC7 — Close sample (guardrails)
// Story 3: A clerk closes an analyzed sample with a verdict. Closing may
// recalculate the parent direction status inside ONE Unit of Work.
//
// Covers:
//   UC7 — POST /samples/{id}/close unknown sample → 404
//   AC: missing verdict → 422
//
// Run: k6 run tests/k6/scenarios/workflow/uc7_close_sample.js

import { check } from 'k6';
import http from '../../helper/http.js';
import { ACTOR_ID, BASE, JSON_HEADERS, unknownId } from './_shared.js';

export const options = {
  scenarios: {
    uc7: {
      executor: 'shared-iterations', exec: 'run', vus: 1, iterations: 1,
      tags: { context: 'workflow', uc: 'UC7', title: 'Close sample', story: 'Story 3', actor: 'staff' },
    },
  },
  thresholds: {
    http_req_duration: [{ threshold: 'p(95)<2000' }],
  },
};

export function run() {
  const id = unknownId();

  const notFound = http.post(
    `${BASE}/samples/${id}/close`,
    JSON.stringify({ actor_id: ACTOR_ID, verdict: 'conforms' }),
    { headers: JSON_HEADERS, expectedStatus: 404 },
  );
  check(notFound, { 'UC7 POST /samples/{id}/close → 404': (r) => r.status === 404 });

  const missing = http.post(
    `${BASE}/samples/${id}/close`,
    JSON.stringify({ actor_id: ACTOR_ID }),
    { headers: JSON_HEADERS, expectedStatus: 422 },
  );
  check(missing, { 'UC7 POST /samples/{id}/close → 422': (r) => r.status === 422 });
}
