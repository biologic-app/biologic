// _shared.js — helpers for the laboratory_workflow k6 suite.
//
// The workflow *command* endpoints (status lifecycle) authorize via an
// `actor_id` field in the request body — there is no bearer token on this
// surface (see laboratory_workflow/presentation/router.py). So unlike the
// staraudio identity/cart suites, these scenarios need no auth helper.
//
// This suite is a deterministic CONTRACT/GUARDRAIL matrix: it asserts the
// negative-path behaviour of every command family against a migrated (but not
// necessarily seeded) database — unknown entity → 404, invalid payload → 422.
// These paths reach the repository through the single Unit of Work and prove
// the command path rolls back cleanly without partial writes. The happy-path
// lifecycle (draft → registered → … → completed) needs orchestrated reference
// data and is intentionally left as a follow-up (documented in index.js).

export const BASE = __ENV.BASE_URL || 'http://localhost:8080/api/v1';

export const JSON_HEADERS = { 'Content-Type': 'application/json' };

// A random, almost-certainly-absent UUIDv4. Used to drive the 404 paths.
export function unknownId() {
  const hex = '0123456789abcdef';
  let s = '';
  for (let i = 0; i < 32; i += 1) {
    if (i === 12) s += '4';
    else if (i === 16) s += hex[8 + Math.floor(Math.random() * 4)];
    else s += hex[Math.floor(Math.random() * 16)];
  }
  return (
    `${s.slice(0, 8)}-${s.slice(8, 12)}-${s.slice(12, 16)}-` +
    `${s.slice(16, 20)}-${s.slice(20)}`
  );
}

// A fixed actor UUID — the command authorizer. Any UUID is accepted by the
// schema; the negative paths fail on entity lookup, not on the actor.
export const ACTOR_ID = '00000000-0000-0000-0000-0000000000aa';
