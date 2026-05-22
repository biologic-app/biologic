---
icon: ListChecks
tags:
  - backend
  - api
  - plan
  - validation
---

# API Resource Ownership And Validation Implementation Plan

> Based on `docs/superpowers/specs/2026-05-22-api-resource-ownership-validation-design.md`.

## Global Task

Split the flat `/api/v1` CRUD surface by bounded-context ownership without changing public paths. Replace the current all-resource catalogs catch-all with context-owned route modules and strict request validation for catalogs, workflow CRUD, and access-control CRUD.

The implementation must keep these public paths stable:

- `/api/v1/branches`, `/api/v1/labs`, `/api/v1/objects`, and other catalog resources.
- `/api/v1/directions`, `/api/v1/samples`, `/api/v1/research`, `/api/v1/tests`, `/api/v1/protocols`.
- `/api/v1/users`, `/api/v1/roles`, `/api/v1/permissions`, `/api/v1/role_permissions`, `/api/v1/user_scopes`.
- Existing workflow command paths such as `/api/v1/directions/{id}/register`.
- Existing alert command paths.

## Test-First Scope

Write the full contract test set before changing production routers or schemas.

Target test files:

- `tests/contexts/catalogs/test_catalog_crud_contract.py`
- `tests/contexts/laboratory_workflow/test_workflow_crud_contract.py`
- `tests/contexts/access_control/test_access_control_crud_contract.py`
- Existing `tests/api/test_workflow_commands.py` remains the regression suite for workflow commands.

Required test coverage:

- Catalog create accepts only the explicit schema for each editable catalog resource.
- Catalog create/update reject unknown fields with `422`.
- Status resources allow reads but reject writes with `409 resource_read_only`.
- Catalog router does not own workflow resources, access-control resources, `alerts`, or `history`.
- Workflow CRUD lives under existing flat paths.
- `PATCH /api/v1/directions/{id}`, `/samples/{id}`, `/research/{id}`, and `/tests/{id}` reject `status_id` with `409 invalid_status_transition`.
- `POST /api/v1/tests` rejects generic creation with `409`.
- Access-control CRUD lives under existing flat paths.
- `POST /api/v1/users` uses access-control validation and rejects catalog-only fields.
- Existing workflow command endpoints still return the same response envelope and `meta.operation`.

The first test run must fail because the current catalogs route still accepts all registered resources and loose payload dictionaries.

## Solution

### Catalogs

Replace `src/contexts/catalogs/presentation/router.py` with a catalog-only route module.

Create strict catalog request schemas in:

- `src/contexts/catalogs/presentation/schemas.py`

Use `ConfigDict(extra="forbid")` for all create and update request models.

Catalog resources:

- Editable: `branches`, `labs`, `objects`, `doctors`, `sample_types`, `research_goals`, `indicators`, `conclusions`, `protocol_types`.
- Read-only: `direction_statuses`, `sample_statuses`, `research_statuses`, `test_statuses`.

The catalog router may use small shared helper functions for response envelopes, but each public route should be bound to a concrete Pydantic request model so OpenAPI shows the actual contract.

### Laboratory Workflow

Move workflow CRUD ownership into `src/contexts/laboratory_workflow/presentation/router.py` or a sibling module imported by that router.

Add workflow CRUD request schemas in:

- `src/contexts/laboratory_workflow/presentation/schemas.py`

Preserve existing command schemas and command endpoints.

Workflow CRUD rules:

- `directions`, `samples`, `research`, and `tests` reject `status_id` in `PATCH`.
- `tests` rejects generic `POST`.
- `protocols` keep command-specific create/update behavior already present.
- Existing command endpoints continue to call `WorkflowCommandService`.

### Access Control

Add an access-control router:

- `src/contexts/access_control/presentation/router.py`

Add access-control request schemas:

- `src/contexts/access_control/presentation/schemas.py`

Register CRUD routes for:

- `users`
- `roles`
- `permissions`
- `role_permissions`
- `user_scopes`

The first implementation can keep placeholder response bodies consistent with the existing CRUD shell, but payload validation must be strict and context-owned.

### Audit And Notifications

Keep notification command routes in `src/contexts/notifications/presentation/router.py`.

Remove `alerts` and `history` from catalogs ownership. If `history` still needs a read route in this patch, add a minimal read-only audit router in:

- `src/contexts/audit/presentation/router.py`

### API Router Assembly

Update `src/api/v1/router.py` so it includes:

- workflow router
- notifications router
- access-control router
- audit router if implemented
- catalogs router

Router inclusion must not depend on a global catch-all accepting resources from other contexts.

## Verification

Run targeted failing tests after writing the tests:

```bash
uv run pytest tests/contexts/catalogs tests/contexts/laboratory_workflow/test_workflow_crud_contract.py tests/contexts/access_control/test_access_control_crud_contract.py tests/api/test_workflow_commands.py -v
```

Expected before production changes: failures showing missing strict validation and incorrect route ownership.

Run targeted tests after implementation:

```bash
uv run pytest tests/contexts/catalogs tests/contexts/laboratory_workflow/test_workflow_crud_contract.py tests/contexts/access_control/test_access_control_crud_contract.py tests/api/test_workflow_commands.py -v
```

Expected after implementation: all targeted tests pass.

Run broader checks before completion:

```bash
uv run ruff check .
uv run black --check .
uv run mypy --strict src
uv run pytest --cov=src --cov-report=term-missing
```

If existing unrelated worktree changes affect the broad checks, record the exact failing command and failure source in the final report.
