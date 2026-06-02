# Catalog CRUD and Status Rename Design

## Purpose

Implement backend-backed CRUD for laboratory reference dictionaries used by the frontend:
objects, sample types, branches, doctors, laboratories, research goals, indicators,
conclusions, and protocol types.

Status dictionaries are handled differently because workflow logic depends on stable
status `code` values. Direction, sample, research, and test statuses can be viewed
and renamed through `name`, but cannot be created, deleted, or have `code` changed.

## Scope

In scope:

- Keep ordinary catalog resources as full CRUD:
  `GET /{resource}`, `GET /{resource}/{id}`, `POST /{resource}`,
  `PATCH /{resource}/{id}`, and `DELETE /{resource}/{id}`.
- Ordinary catalog deletes remain soft deletes when the table has `deleted_at`.
- Add status rename support:
  `PATCH /direction_statuses/{id}`, `PATCH /sample_statuses/{id}`,
  `PATCH /research_statuses/{id}`, and `PATCH /test_statuses/{id}`.
- Status rename accepts only `name`.
- Keep status `GET` list/detail endpoints.
- Keep status `POST` and `DELETE` forbidden.
- Keep permissions and data-access scope unchanged.
- Align frontend dictionary forms so status dictionaries edit only `name`.

Out of scope:

- Changing RBAC permissions or scope rules.
- Changing workflow status transition policies.
- Adding new status codes from the UI.
- Hard-deleting catalog rows.
- Reworking the generic CRUD UI layout.

## Backend Design

The existing `contexts/catalogs` bounded context remains the owner of reference
dictionary CRUD.

Ordinary dictionaries already use repository methods for list, read, create,
update, and delete. This behavior stays unchanged, with tests covering the public
contract where needed.

Status resources get update methods only:

- `DirectionStatusRepository.update`
- `SampleStatusRepository.update`
- `ResearchStatusRepository.update`
- `TestStatusRepository.update`

Each update method reads the row by ID, applies only `name`, updates `updated_at`,
commits, refreshes, and returns the row.

The catalog use case adds:

- `update_direction_status`
- `update_sample_status`
- `update_research_status`
- `update_test_status`

Each method serializes the status with existing status fields and returns operation
metadata such as `direction_statuses.update`.

The presentation layer adds a strict `StatusUpdateRequest` schema:

```python
class StatusUpdateRequest(StrictRequest):
    name: str
```

Status `PATCH` endpoints accept this schema and return the standard
`SingleResponse[dict[str, object]]` envelope. Extra fields such as `code` are
rejected with `422` because schemas use `extra="forbid"`.

Status `POST` and `DELETE` endpoints keep returning `409 resource_read_only` to
preserve the existing contract that status sets are not managed as ordinary
catalog rows.

## Frontend Design

The existing dictionaries page and `DictionaryCrudContent` remain the frontend
entry point.

Ordinary dictionary configs remain full CRUD. The shared CRUD UI already supports:

- list loading from backend list endpoints,
- detail viewing,
- create modal,
- edit modal,
- delete confirmation,
- bulk delete.

Status dictionary configs are adjusted so edit/create form fields expose only:

- `name`

The table and detail view still show `code` for operator context, but the form
does not submit `code`. Since frontend permissions are not changed in this task,
the backend remains the source of truth for preventing status creation and deletion.

The generic UI may still render create/delete controls based on existing
permissions. If a user attempts unsupported status create/delete, the backend
returns `409 resource_read_only`. A future permission/UI refinement can hide those
actions per resource, but this task does not change access-control behavior.

## Error Handling

- Missing status ID: existing `NotFoundError` behavior returns `404`.
- Status `PATCH` with `code` or other extra fields: FastAPI/Pydantic validation
  returns `422`.
- Status `POST`: `409 resource_read_only`.
- Status `DELETE`: `409 resource_read_only`.
- Ordinary catalog validation remains resource-specific and strict.

## Testing

Backend contract tests cover:

- ordinary catalog create still works,
- unknown ordinary catalog fields are rejected,
- status list still returns the list envelope,
- status `PATCH` with `name` returns `200` and operation metadata,
- status `PATCH` with `code` is rejected with `422`,
- status `POST` remains `409 resource_read_only`,
- status `DELETE` remains `409 resource_read_only`.

Frontend verification covers:

- lint,
- typecheck,
- build,
- status dictionary config fields submit only `name`.

## Acceptance Criteria

- Ordinary dictionaries listed in the request support backend create, view, edit,
  and soft-delete.
- Status dictionaries support view and rename of `name`.
- Status `code` cannot be changed through the API.
- Status rows cannot be created or deleted through catalog CRUD.
- Existing workflow status-code logic is not changed.
- Backend tests pass for the catalog contract.
- Frontend typecheck/build pass after config changes.
