---
icon: Route
tags:
  - backend
  - api
  - ddd
  - validation
---

# API Resource Ownership And Validation Design

Date: 2026-05-22

## Purpose

The current CRUD API uses one dynamic route that accepts any registered resource and loosely typed payloads. This hides bounded-context ownership, lets catalog endpoints accept arbitrary fields, and mixes catalog, workflow, access-control, system, and audit resources in one presentation module.

This change keeps the public API paths stable while splitting route ownership by bounded context and adding strict request validation for reference catalogs.

## Goals

- Keep existing flat public paths under `/api/v1`.
- Move each resource family to its owning bounded context.
- Add strict Pydantic create/update schemas for every catalog resource.
- Separate user, role, permission, and scope management from catalog CRUD.
- Preserve workflow command endpoints and add workflow-specific CRUD rules.
- Remove the generic all-resource CRUD surface from the catalogs context.

## Public API Shape

Public paths remain flat and backward-compatible:

```http
GET    /api/v1/branches
POST   /api/v1/branches
PATCH  /api/v1/branches/{id}

GET    /api/v1/directions
PATCH  /api/v1/directions/{id}
POST   /api/v1/directions/{id}/register

GET    /api/v1/users
POST   /api/v1/users
PATCH  /api/v1/users/{id}
```

No `/catalogs`, `/workflow`, or `/access-control` namespace is introduced in this iteration.

## Resource Ownership

| Context | Owned resources |
| --- | --- |
| `catalogs` | `branches`, `labs`, `objects`, `doctors`, `sample_types`, `research_goals`, `indicators`, `conclusions`, `protocol_types`, `direction_statuses`, `sample_statuses`, `research_statuses`, `test_statuses` |
| `laboratory_workflow` | `directions`, `samples`, `research`, `tests`, `protocols` |
| `access_control` | `users`, `roles`, `permissions`, `role_permissions`, `user_scopes` |
| `notifications` | `alerts` commands and alert user actions |
| `audit` | `history` read-only access |

The `catalogs` presentation layer must not register routes for workflow, access-control, notification, or audit resources.

## Catalog Validation

Catalog create and update payloads use one explicit Pydantic schema per resource. All catalog schemas must reject unknown fields with `extra="forbid"`.

Catalog resources and accepted payload fields:

| Resource | Create/update fields |
| --- | --- |
| `branches` | `code`, `name` |
| `labs` | `branch_id`, `code`, `name`, `full_name` |
| `objects` | `branch_id`, `code`, `name`, `full_name`, `address` |
| `doctors` | `first_name`, `last_name`, `patronymic` |
| `sample_types` | `code`, `name` |
| `research_goals` | `code`, `name`, `comment`, `lab_id` |
| `indicators` | `name`, `unit`, `norm_text`, `norm_value`, `default_text`, `comment`, `research_goal_id`, `sample_type_id` |
| `conclusions` | `code`, `name`, `text_singular`, `text_plural`, `comment` |
| `protocol_types` | `code`, `name` |

Create schemas enforce required model fields that are non-null in the current database model. Update schemas allow partial payloads but still reject unknown fields.

Status resources are read-only through operational CRUD:

- `direction_statuses`
- `sample_statuses`
- `research_statuses`
- `test_statuses`

`GET` and `GET /{id}` are allowed for status resources. `POST`, `PATCH`, and `DELETE` return `409 resource_read_only`.

## Workflow CRUD Rules

Workflow CRUD stays on the current resource paths:

- `directions`
- `samples`
- `research`
- `tests`
- `protocols`

Workflow CRUD belongs to `src/contexts/laboratory_workflow/presentation`, not `catalogs`.

Rules:

- `directions`, `samples`, `research`, and `tests` cannot change `status_id` through `PATCH`.
- `tests` cannot be created through generic CRUD; tests are created by research assignment or add-tests commands.
- Lifecycle changes stay on command endpoints such as `POST /directions/{id}/register`, `POST /samples/{id}/reject`, and `POST /tests/{id}/complete`.
- `protocols` can keep its existing command-specific create/update behavior while workflow CRUD is separated from catalogs.

## Access-Control CRUD Rules

Access-control resources are managed by `src/contexts/access_control/presentation`:

- `users`
- `roles`
- `permissions`
- `role_permissions`
- `user_scopes`

Each resource gets its own request schemas. These schemas must not reuse catalog payloads or the generic catalog registry.

Initial access-control validation rules:

- `users` accepts identity, auth, role, lab, and boolean role marker fields that exist on the `User` model.
- `roles` accepts `key`, `name`, and `scope_type`.
- `permissions` accepts `resource` and `action`.
- `role_permissions` accepts `role_id` and `permission_id`.
- `user_scopes` accepts `user_id` and `scope_id`.

Authorization enforcement can continue to evolve separately. This design only separates route ownership and request contracts.

## Audit And Notifications

`alerts` must not be created through generic CRUD. Users can act on alerts through existing notification commands:

```http
POST /api/v1/alerts/{id}/mark-read
POST /api/v1/alerts/{id}/hide
POST /api/v1/alerts/mark-all-read
```

`history` is read-only and belongs to the audit context. If a complete audit router is not implemented in the first patch, the replacement must still prevent catalogs from owning `history`.

## Routing Strategy

Prefer explicit FastAPI route registration per owned resource over a global `/{resource}` catch-all.

For catalogs and access-control, explicit registration is required so generated OpenAPI documents expose concrete request schemas. Shared helper functions may be used to avoid repeated route bodies, but the public routes must be associated with concrete Pydantic request models.

For workflow CRUD, a typed registry is acceptable if it keeps ownership inside `laboratory_workflow` and preserves workflow-specific rules.

Router inclusion order must not be relied on to hide incorrect ownership. A resource should be accepted by exactly one context router.

## Error Contract

The existing problem-details handlers remain in use.

Expected errors:

- Unknown resource path: `404`.
- Extra or invalid request fields: `422`.
- Read-only resource write: `409` with `code="resource_read_only"`.
- Invalid lifecycle status update through CRUD: `409` with `code="invalid_status_transition"`.
- System-created resource write through CRUD: `409` with `code="resource_read_only"` or a more specific existing conflict code.

## Testing Requirements

Contract tests must cover:

- `POST /api/v1/branches` accepts only the branch schema fields.
- `POST /api/v1/branches` with an unknown field returns `422`.
- `POST /api/v1/direction_statuses` returns `409 resource_read_only`.
- `PATCH /api/v1/directions/{id}` with `status_id` returns `409 invalid_status_transition`.
- `POST /api/v1/tests` returns `409`.
- `POST /api/v1/users` uses access-control validation and rejects catalog-only fields.
- Workflow command tests continue to pass on existing paths.

Targeted verification:

```bash
uv run pytest tests/contexts/catalogs tests/contexts/access_control tests/api/test_workflow_commands.py -v
```

Broader verification after implementation:

```bash
uv run ruff check .
uv run black --check .
uv run mypy --strict src
uv run pytest --cov=src --cov-report=term-missing
```
