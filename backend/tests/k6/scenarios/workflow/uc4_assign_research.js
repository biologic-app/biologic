// UC4 — Assign research (guardrails)
// Story 2: A clerk assigns a research goal to a sample. The command creates a
// research aggregate and its child tests in ONE Unit of Work.
//
// Covers:
//   UC4 — POST /samples/{id}/assign-research unknown sample → 404
//   AC: missing research_goal_id → 422
//
// Run: k6 run tests/k6/scenarios/workflow/uc4_assign_research.js

import { check } from 'k6';
import http from '../../helper/http.js';
import { ACTOR_ID, BASE, JSON_HEADERS, unknownId } from './_shared.js';

export const options = {
  scenarios: {
    uc4: {
      executor: 'shared-iterations', exec: 'run', vus: 1, iterations: 1,
      tags: { context: 'workflow', uc: 'UC4', title: 'Assign research', story: 'Story 2', actor: 'staff' },
    },
  },
  thresholds: {
    http_req_duration: [{ threshold: 'p(95)<2000' }],
  },
};

export function run() {
  const sampleId = unknownId();

  const notFound = http.post(
    `${BASE}/samples/${sampleId}/assign-research`,
    JSON.stringify({ actor_id: ACTOR_ID, research_goal_id: unknownId() }),
    { headers: JSON_HEADERS, expectedStatus: 404 },
  );
  check(notFound, { 'UC4 POST /samples/{id}/assign-research → 404': (r) => r.status === 404 });

  const missing = http.post(
    `${BASE}/samples/${sampleId}/assign-research`,
    JSON.stringify({ actor_id: ACTOR_ID }),
    { headers: JSON_HEADERS, expectedStatus: 422 },
  );
  check(missing, { 'UC4 POST /samples/{id}/assign-research → 422': (r) => r.status === 422 });
}
