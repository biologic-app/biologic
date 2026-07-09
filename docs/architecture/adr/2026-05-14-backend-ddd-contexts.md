---
icon: FileDecision
tags:
  - adr
  - backend
  - ddd
---

# ADR: Backend DDD Context Layout

Date: 2026-05-14

## Status

Accepted

## Context

The backend MVP requires CRUD screens, lifecycle commands, permissions, audit, and notifications. A flat module layout would make domain invariants and API plumbing hard to separate.

## Decision

Use `src/contexts/<bounded_context>/{domain,application,infrastructure,presentation}` for business modules and keep cross-context primitives in `src/core`.

`change_log` remains the persistence table for MVP audit history and is exposed through the `history` API resource for compatibility.

## Consequences

- Domain code stays independent from FastAPI and SQLAlchemy.
- Application services depend on ports and DTOs.
- Infrastructure implements repositories and adapters.
- Presentation registers FastAPI routes and maps HTTP schemas to use cases.
- `samples.protocol_id` remains the MVP protocol linkage until a many-to-many sample/protocol table is introduced.
