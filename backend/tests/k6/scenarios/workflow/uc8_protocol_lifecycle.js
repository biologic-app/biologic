// UC8 — Protocol lifecycle (guardrails)
// Story 4: A protocol is created over completed samples, optionally updated,
// then issued (signed). Each step is a command on the single Unit of Work.
//
// Covers:
//   UC8 — PATCH /protocols/{id}      unknown → 404   (update_protocol path)
//   UC8 — POST  /protocols/{id}/issue unknown → 404   (issue_protocol path)
//   AC: create protocol without actor_id → 422
//
// NOTE: create_protocol over unknown sample_ids resolves the SAMPLE_COMPLETED
// status first, so its negative status depends on whether reference data is
// seeded (404 unknown samples vs 409 status_not_configured). We assert the
// seed-independent 422 path here and cover create's 404 in integration tests.
//
// Run: k6 run tests/k6/scenarios/workflow/uc8_protocol_lifecycle.js

import { check } from 'k6';
import http from '../../helper/http.js';
import { ACTOR_ID, BASE, JSON_HEADERS, unknownId } from './_shared.js';

export const options = {
  scenarios: {
    uc8: {
      executor: 'shared-iterations', exec: 'run', vus: 1, iterations: 1,
      tags: { context: 'workflow', uc: 'UC8', title: 'Protocol lifecycle', story: 'Story 4', actor: 'staff' },
    },
  },
  thresholds: {
    http_req_duration: [{ threshold: 'p(95)<2000' }],
  },
};

export function run() {
  const id = unknownId();
  const actor = JSON.stringify({ actor_id: ACTOR_ID });

  const update = http.patch(`${BASE}/protocols/${id}`, actor, { headers: JSON_HEADERS, expectedStatus: 404 });
  check(update, { 'UC8 PATCH /protocols/{id} → 404': (r) => r.status === 404 });

  const issue = http.post(`${BASE}/protocols/${id}/issue`, actor, { headers: JSON_HEADERS, expectedStatus: 404 });
  check(issue, { 'UC8 POST /protocols/{id}/issue → 404': (r) => r.status === 404 });

  const create = http.post(
    `${BASE}/protocols`,
    JSON.stringify({ sample_ids: [unknownId()] }),
    { headers: JSON_HEADERS, expectedStatus: 422 },
  );
  check(create, { 'UC8 POST /protocols → 422': (r) => r.status === 422 });
}
