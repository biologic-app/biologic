// index.js — single entry point for the laboratory_workflow k6 suite.
//
// Run:               k6 run tests/k6/scenarios/workflow/index.js
// Run (custom host): BASE_URL=http://localhost:8080/api/v1 k6 run tests/k6/scenarios/workflow/index.js
// Report:            make k6-workflow   (runs this file with --out json, then renders HTML)
//
// This suite is a CONTRACT/GUARDRAIL matrix for the workflow lifecycle command
// surface (status transitions routed through the single Unit of Work). One
// scenario per command family asserts the seed-independent negative paths —
// unknown entity → 404 (the UoW rolls back, nothing persists) and invalid
// payload → 422 (rejected before the UoW opens). No auth tokens are needed:
// these endpoints authorize via an `actor_id` body field.
//
// FOLLOW-UP (happy-path lifecycle): driving draft → registered → in_progress →
// analyzed → completed end-to-end needs orchestrated reference data (seeded
// status tables, a research_goal with indicators, sample_types). That belongs
// in a setup() that creates the prerequisite aggregates via the CRUD endpoints
// against a `make seed-data` database, and is intentionally left as the next
// extension of this suite.

import { run as _uc1 } from './uc1_register_direction.js';
import { run as _uc2 } from './uc2_register_sample.js';
import { run as _uc3 } from './uc3_reject_sample.js';
import { run as _uc4 } from './uc4_assign_research.js';
import { run as _uc5 } from './uc5_research_transitions.js';
import { run as _uc6 } from './uc6_test_transitions.js';
import { run as _uc7 } from './uc7_close_sample.js';
import { run as _uc8 } from './uc8_protocol_lifecycle.js';

export function uc1() { return _uc1(); }
export function uc2() { return _uc2(); }
export function uc3() { return _uc3(); }
export function uc4() { return _uc4(); }
export function uc5() { return _uc5(); }
export function uc6() { return _uc6(); }
export function uc7() { return _uc7(); }
export function uc8() { return _uc8(); }

export const options = {
  // Same descriptive tag block as each standalone UC file — k6 stamps these
  // onto every metric point so the HTML report renders titles + meta chips.
  scenarios: {
    uc1: { executor: 'shared-iterations', exec: 'uc1', vus: 1, iterations: 1,
      tags: { context: 'workflow', uc: 'UC1', title: 'Register direction', story: 'Story 1', actor: 'staff' } },
    uc2: { executor: 'shared-iterations', exec: 'uc2', vus: 1, iterations: 1,
      tags: { context: 'workflow', uc: 'UC2', title: 'Register sample', story: 'Story 1', actor: 'staff' } },
    uc3: { executor: 'shared-iterations', exec: 'uc3', vus: 1, iterations: 1,
      tags: { context: 'workflow', uc: 'UC3', title: 'Reject sample', story: 'Story 1', actor: 'staff' } },
    uc4: { executor: 'shared-iterations', exec: 'uc4', vus: 1, iterations: 1,
      tags: { context: 'workflow', uc: 'UC4', title: 'Assign research', story: 'Story 2', actor: 'staff' } },
    uc5: { executor: 'shared-iterations', exec: 'uc5', vus: 1, iterations: 1,
      tags: { context: 'workflow', uc: 'UC5', title: 'Research transitions', story: 'Story 2', actor: 'staff' } },
    uc6: { executor: 'shared-iterations', exec: 'uc6', vus: 1, iterations: 1,
      tags: { context: 'workflow', uc: 'UC6', title: 'Test transitions', story: 'Story 3', actor: 'staff' } },
    uc7: { executor: 'shared-iterations', exec: 'uc7', vus: 1, iterations: 1,
      tags: { context: 'workflow', uc: 'UC7', title: 'Close sample', story: 'Story 3', actor: 'staff' } },
    uc8: { executor: 'shared-iterations', exec: 'uc8', vus: 1, iterations: 1,
      tags: { context: 'workflow', uc: 'UC8', title: 'Protocol lifecycle', story: 'Story 4', actor: 'staff' } },
  },
  thresholds: {
    // Every check is a deliberate negative path (4xx), so http_req_failed can
    // never be <1%. Gate correctness on checks instead; keep latency as a
    // guardrail. (See k6-scenario-authoring skill, gotcha #2.)
    checks: [{ threshold: 'rate==1.00' }],
    http_req_duration: [{ threshold: 'p(95)<2000' }],
  },
};
