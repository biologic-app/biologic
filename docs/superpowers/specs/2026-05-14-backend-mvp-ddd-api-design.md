# Backend MVP DDD API Design

Date: 2026-05-14

## Purpose

This document defines the backend MVP contract for the laboratory workflow system. It is a technical backend specification, not a database-only schema. It combines:

- DDD aggregate boundaries and invariants.
- A uniform CRUD API for resource-oriented screens.
- Command endpoints for business lifecycle transitions.
- Permission and scope rules.
- Audit, notification, validation, and error contracts.

The frontend currently expects a mixed CRUD + command API under `/api/v1`, snake_case payloads, UUID identifiers, list pagination, `include` support, and problem-details style errors.

## MVP Scope

The MVP covers the first full operational workflow:

1. Import or manually create a direction.
2. Keep the direction editable while it is in `draft`.
3. Register the direction.
4. Register or reject samples.
5. Assign research goals to samples.
6. Confirm, start, and reject research.
7. Start, complete, requeue, and reject tests.
8. Automatically recalculate research, sample, and direction statuses.
9. Close a sample with a verdict.
10. Create and issue a protocol.
11. Write audit history and create alerts for the workflow.
12. Enforce permissions and scopes for all reads and commands.

Out of scope for MVP:

- Separate CRUD resource `results`.
- Full protocol approval workflow.
- Separate `import_issues` table.
- Reports beyond read-only dashboard/list aggregates.
- Editing completed operational entities.
- Full printable document template builder.

Core rule: operational statuses cannot be changed with `PATCH status_id`. Lifecycle transitions must go through commands.

## Bounded Contexts

### Laboratory Workflow

The primary MVP bounded context. It owns the lifecycle of directions, samples, research, tests, and protocols.

### Supporting Contexts

- Access Control: users, roles, permissions, role permissions, and user scopes.
- Catalogs: branches, labs, objects, doctors, sample types, research goals, indicators, conclusions, protocol types, and status tables.
- Audit: immutable `history` entries for CRUD and domain events.
- Notifications: system-created `alerts` and user visibility commands.

## Aggregates

### Direction Aggregate

Root: `Direction`.

Owns:

- Direction status.
- `import_warnings`.
- Link to object, doctor, and branch context.
- `draft -> registered` rule.
- Overall direction state derived from samples: `in_progress`, `partially_completed`, `completed`.

Commands:

- `ImportDirection`
- `CreateDirection`
- `UpdateDraftDirection`
- `RegisterDirection`

After samples are created, their own lifecycle belongs to the Sample aggregate.

### Sample Aggregate

Root: `Sample`.

Owns:

- Sample status.
- `received_at`, `deadline`, `completed_at`.
- `sample_type_id`.
- `verdict`.
- Rejection and closing rules.
- Rule that new research cannot be assigned after `completed`.

Commands:

- `RegisterSample`
- `RejectSample`
- `AssignResearchToSample`
- `CloseSample`

### Research Aggregate

Root: `Research`.

Owns:

- Research status.
- Link to `sample_id`, `research_goal_id`, and `lab_id`.
- Creating tests from indicators.
- Rule that research becomes `completed` when all active tests are terminal.

Commands:

- `ConfirmResearch`
- `RejectResearch`
- `StartResearch`
- `AddTestsToResearch`

### Test Operational Aggregate

`Test` depends on `Research`, but has command endpoints because the UI and permission matrix operate on test queues directly.

Owns:

- Test status.
- Result `value`.
- Norm snapshot `norm`.
- `is_active`.
- Rejection reason.

Commands:

- `StartTest`
- `CompleteTest`
- `RequeueTest`
- `RejectTest`

Test invariants must still check the related Research and Sample.

### Protocol Aggregate

Root: `Protocol`.

Owns:

- Samples included in the protocol.
- Conclusion and protocol type.
- Issue state.
- Rule that a protocol can be created only from closed samples.

Commands:

- `CreateProtocol`
- `UpdateProtocol`
- `IssueProtocol`

## Common API Contract

Base prefix:

```http
/api/v1
```

General rules:

- Payloads use `snake_case`.
- IDs are UUIDs.
- Timestamps are ISO 8601 strings with timezone.
- Soft-deleted rows are excluded by default.
- The backend applies permission and scope filters; frontend filters are not security controls.

### CRUD Shape

CRUD resources use:

```http
GET    /{resource}
GET    /{resource}/{id}
POST   /{resource}
PATCH  /{resource}/{id}
DELETE /{resource}/{id}
```

List query parameters:

- `limit`: integer, default `50`, maximum decided by backend.
- `cursor`: opaque string returned as `next_cursor` from the previous page.
- `sort_by`: field path, for example `created_at` or `status.name`.
- `sort_order`: `asc` or `desc`.
- `filters`: JSON string.
- `include`: comma-separated relation names.

List response:

```json
{
  "items": [],
  "meta": {
    "timestamp": "2026-05-14T10:00:00Z",
    "request_id": "uuid-or-null",
    "version": "v1",
    "total": 120,
    "limit": 50,
    "next_cursor": null,
    "has_more": true,
    "includes_requested": ["status"],
    "includes_applied": ["status"],
    "includes_allowed": ["status", "lab"]
  }
}
```

Read response:

```json
{
  "data": {},
  "meta": {
    "timestamp": "2026-05-14T10:00:00Z",
    "request_id": "uuid-or-null",
    "version": "v1",
    "includes": ["status"],
    "includes_requested": ["status"],
    "includes_applied": ["status"],
    "includes_allowed": ["status"]
  }
}
```

### Command Shape

Commands use `POST`:

```http
POST /directions/{id}/register
POST /samples/{id}/reject
POST /tests/{id}/complete
```

Command response returns the updated primary entity without deep includes:

```json
{
  "data": {
    "id": "uuid",
    "status_id": "uuid",
    "updated_at": "2026-05-14T10:00:00Z"
  },
  "meta": {
    "timestamp": "2026-05-14T10:00:00Z",
    "request_id": "uuid-or-null",
    "version": "v1",
    "operation": "samples.reject"
  }
}
```

When the UI needs a full card after a command, it must issue a follow-up `GET` with the required `include` value.

### Status Representation

Operational rows store normalized status IDs. With `include=status`, responses include stable codes:

```json
{
  "status_id": "uuid",
  "status": {
    "id": "uuid",
    "code": "registered",
    "name": "Зарегистрирован"
  }
}
```

Status reference tables:

- `direction_statuses`
- `sample_statuses`
- `research_statuses`
- `test_statuses`

## MVP Data Model Notes

This section lists backend-relevant fields and relationships. It does not replace migration definitions.

### Required Additions Or Clarifications

- `directions.import_warnings jsonb null`: warnings created during file import.
- `samples.deadline timestamptz null`: calculated when a sample is registered.
- `samples.verdict text null`: final verdict set when a sample is closed.
- `research.lab_id uuid not null`: denormalized or direct relation to enforce lab scope efficiently.
- Protocol to samples relation is required. Use either `samples.protocol_id` for simple MVP or a join table if one protocol can include many samples and samples can move between protocols. MVP may keep `samples.protocol_id` if one sample belongs to at most one protocol.

### Working Entities

`directions`:

- `id`, `year_no`, `base_no`, `is_done`, `is_urgent`
- `doctor_id`, `object_id`, `status_id`
- `import_warnings`
- `sampled_at`, `received_at`, `completed_at`
- audit fields and soft delete fields

`samples`:

- `id`, `month_no`, `name`, `alternate_name`, `mass`
- `target_description`, `comment`, `section`, `delivery`
- `nomenclature_code`, `batch_code`, `supplier`
- `is_urgent`, `is_done`
- `sample_type_id`, `status_id`, `direction_id`, `protocol_id`
- `sampled_at`, `received_at`, `deadline`, `completed_at`
- `verdict`
- audit fields and soft delete fields

`research`:

- `id`, `sample_id`, `research_goal_id`, `lab_id`, `status_id`
- `comment`, `recommendation`
- `received_at`, `completed_at`
- audit fields and soft delete fields

`tests`:

- `id`, `research_id`, `indicator_id`, `status_id`
- `value`, `norm`, `comment`, `is_active`
- `rejection_reason`
- audit fields and soft delete fields

`protocols`:

- `id`, `year_no`, `copies`, `is_signed`
- `protocol_copy_name`, `excerpt_copy_name`
- `conclusion_id`, `protocol_type_id`
- `issued_at`
- audit fields and soft delete fields

## Read And CRUD Resources

### Catalog CRUD

Standard CRUD:

- `branches`
- `labs`
- `objects`
- `doctors`
- `sample_types`
- `research_goals`
- `indicators`
- `conclusions`
- `protocol_types`

Status tables are read-only for operational users and admin-only for seed/maintenance:

- `direction_statuses`
- `sample_statuses`
- `research_statuses`
- `test_statuses`

### Access Control CRUD

MVP required:

- `users`
- `roles`
- `user_scopes`

Seeded and optionally admin-editable:

- `permissions`
- `role_permissions`

### Workflow Resources

- `directions`
- `samples`
- `research`
- `tests`
- `protocols`
- `alerts`
- `history`

Rules:

- `history` is read-only.
- `alerts` are system-created; users can mark as read or hide them.
- `tests` are system-created from research assignment or added through `research.add-tests`.
- `directions`, `samples`, `research`, and `tests` cannot change lifecycle status through CRUD patch.

## Commands By Aggregate

### Direction Commands

#### Import Direction

```http
POST /directions/import
Content-Type: multipart/form-data
```

Request fields:

- `file`: required import file.
- Optional import options may be added later, but are not required for MVP.

Behavior:

- Parses the uploaded file.
- Creates a direction in `draft`.
- Creates samples in `pending`.
- Saves non-blocking warnings to `directions.import_warnings`.
- Rejects the request without writes only for blocking errors, such as unreadable file, unknown required structure, or missing direction identity fields.
- Writes `history`.

Response:

- Command response with created direction.
- Include warning summary in `data.import_warnings`.

Blocking errors:

- `400` invalid file format.
- `422` validation failed for required import structure.

#### Create Direction

```http
POST /directions
```

Creates a manual `draft` direction.

Allowed roles:

- `registrar`
- `developer`

#### Update Draft Direction

```http
PATCH /directions/{id}
```

Allowed only when direction status is `draft`. It may update editable draft fields, but not `status_id`.

Domain errors:

- `409 direction_not_editable` if status is not `draft`.

#### Register Direction

```http
POST /directions/{id}/register
```

Allowed from:

- `draft`

Request:

```json
{
  "comment": "Ready for laboratory workflow"
}
```

Behavior:

- Validates that required sample data is present.
- Validates that research assignments exist where required by the workflow.
- Changes direction `draft -> registered`.
- Writes `history`.
- Emits `DirectionRegistered`.

### Sample Commands

#### Add Sample To Direction

```http
POST /directions/{id}/samples
```

Creates a `pending` sample for a `draft` direction.

#### Update Sample

```http
PATCH /samples/{id}
```

May update editable fields until terminal statuses. It must not update `status_id`.

#### Register Sample

```http
POST /samples/{id}/register
```

Allowed from:

- `pending`

Request:

```json
{
  "received_at": "2026-05-14T10:00:00Z",
  "deadline": "2026-05-16T10:00:00Z"
}
```

If `deadline` is omitted, backend calculates it using `DeadlinePolicy`.

Behavior:

- Changes `pending -> registered`.
- Sets `received_at`.
- Sets or calculates `deadline`.
- Writes `history`.

#### Reject Sample

```http
POST /samples/{id}/reject
```

Allowed from:

- `pending`

Request:

```json
{
  "reason": "Damaged container"
}
```

Behavior:

- Changes sample `pending -> rejected`.
- Rejects all research and active tests for the sample.
- Uses `cancellation_reason = "sample_rejected"` for cascaded changes.
- Recalculates direction status.
- Writes `history` for each changed entity.
- Emits alert events.

#### Assign Research To Sample

```http
POST /samples/{id}/assign-research
```

Allowed when sample is not `completed` or `rejected`.

Request:

```json
{
  "research_goal_id": "uuid",
  "comment": "Optional"
}
```

Behavior:

- Creates `research` in `draft`.
- Sets `research.lab_id` from the research goal.
- Creates `tests queued` from active indicators for the research goal and sample type.
- Writes `history`.

#### Close Sample

```http
POST /samples/{id}/close
```

Allowed from:

- `analyzed`

Request:

```json
{
  "verdict": "compliant",
  "comment": "All research is complete"
}
```

Behavior:

- Requires all research for the sample to be terminal.
- Changes sample `analyzed -> completed`.
- Sets `verdict` and `completed_at`.
- Prevents future research/test assignment for the sample.
- Recalculates direction status.
- Writes `history`.
- Emits alert events if verdict is non-compliant.

### Research Commands

#### Confirm Research

```http
POST /research/{id}/confirm
```

Allowed from:

- `draft`

Behavior:

- Changes `draft -> ordered`.
- Writes `history`.

#### Reject Research

```http
POST /research/{id}/reject
```

Allowed from:

- `draft`
- `ordered`

Request:

```json
{
  "reason": "Not applicable"
}
```

Behavior:

- Changes research to `rejected`.
- Rejects or deactivates active tests.
- Recalculates sample state.
- Writes `history`.

#### Start Research

```http
POST /research/{id}/start
```

Allowed from:

- `ordered`

Behavior:

- Changes `ordered -> in_progress`.
- If sample is `registered`, changes sample to `in_progress`.
- If direction is `registered`, changes direction to `in_progress`.
- Writes `history`.

#### Add Tests To Research

```http
POST /research/{id}/add-tests
```

Allowed for lab chief when sample is not closed.

Request:

```json
{
  "indicator_ids": ["uuid"],
  "reason": "Additional measurement required"
}
```

Behavior:

- Creates new `tests queued`.
- If research was `completed`, changes it to `in_progress`.
- If sample was `analyzed`, changes it to `in_progress`.
- If direction was `partially_completed`, may change it to `in_progress`.
- Writes `history`.

### Test Commands

#### Start Test

```http
POST /tests/{id}/start
```

Allowed from:

- `queued`

Behavior:

- Changes `queued -> in_progress`.
- Writes `history`.

#### Complete Test

```http
POST /tests/{id}/complete
```

Allowed from:

- `in_progress`

Request:

```json
{
  "value": "0.3",
  "norm": "not more than 0.5",
  "comment": "Within reference"
}
```

Behavior:

- Changes `in_progress -> completed`.
- Saves value, norm snapshot, and comment.
- If all active tests are terminal, changes research to `completed`.
- If all research for the sample is terminal, changes sample to `analyzed`.
- Recalculates direction status.
- Writes `history`.
- Emits completion alert events.

#### Requeue Test

```http
POST /tests/{id}/requeue
```

Allowed from:

- `in_progress`

Behavior:

- Changes `in_progress -> queued`.
- Writes `history`.

#### Reject Test

```http
POST /tests/{id}/reject
```

Allowed from:

- `queued`
- `in_progress`

Request:

```json
{
  "reason": "Measurement not required"
}
```

Behavior:

- Changes test to `rejected`.
- Sets `rejection_reason`.
- Recalculates research and sample state if needed.
- Writes `history`.

### Protocol Commands

#### Create Protocol

```http
POST /protocols
```

Request:

```json
{
  "sample_ids": ["uuid"],
  "protocol_type_id": "uuid",
  "conclusion_id": "uuid",
  "copies": 2
}
```

Behavior:

- Requires all samples to be `completed`.
- Links samples to the protocol.
- Creates protocol draft row.
- Writes `history`.

#### Update Protocol

```http
PATCH /protocols/{id}
```

Allowed while protocol is not issued.

#### Issue Protocol

```http
POST /protocols/{id}/issue
```

Behavior:

- Sets `issued_at`.
- Sets `is_signed = true` for MVP unless signature is later split into a separate workflow.
- Writes `history`.
- Emits `ProtocolIssued` and `protocol_ready` alerts.

### Alert Commands

```http
POST /alerts/{id}/mark-read
POST /alerts/{id}/hide
POST /alerts/mark-all-read
```

Rules:

- Only alert owner can run these commands.
- Alerts are not physically deleted by users.

## Domain Events And Cascades

Synchronous cascades run in the same transaction when they are required for status consistency. Alert creation may be asynchronous through a notification policy or worker.

### Synchronous Events

`DirectionImported`:

- Creates direction `draft`.
- Creates samples `pending`.
- Saves import warnings.
- Writes history.

`DirectionRegistered`:

- Changes direction `draft -> registered`.
- Writes history.
- Emits notification event for sanitary inspector.

`SampleRegistered`:

- Changes sample `pending -> registered`.
- Sets `received_at`.
- Sets `deadline`.
- Writes history.

`SampleRejected`:

- Changes sample `pending -> rejected`.
- Changes all sample research to `rejected`.
- Changes active tests to `rejected` or inactive.
- Sets cancellation reason `sample_rejected`.
- Recalculates direction status.
- Writes history for each changed entity.

`ResearchAssigned`:

- Creates research `draft`.
- Creates tests `queued`.
- Writes history.

`ResearchConfirmed`:

- Changes research `draft -> ordered`.
- Writes history.

`ResearchStarted`:

- Changes research `ordered -> in_progress`.
- Changes sample `registered -> in_progress` if needed.
- Changes direction `registered -> in_progress` if needed.
- Writes history.

`TestCompleted`:

- Changes test `in_progress -> completed`.
- Completes research when all active tests are terminal.
- Changes sample to `analyzed` when all research is terminal.
- Changes direction to `partially_completed` when at least one sample is closed but not all are closed.
- Writes history.

`TestsAddedToResearch`:

- Creates tests `queued`.
- Changes research `completed -> in_progress` if needed.
- Changes sample `analyzed -> in_progress` if needed.
- Changes direction `partially_completed -> in_progress` if needed.
- Writes history.

`SampleClosed`:

- Changes sample `analyzed -> completed`.
- Sets verdict.
- Changes direction to `completed` when all samples are closed or rejected.
- Writes history.

`ProtocolIssued`:

- Sets protocol issue fields.
- Writes history.
- Emits protocol alerts.

### Alert Events

The notification policy creates `alerts` for:

- `sample_rejected`
- `sample_deadline_overdue`
- `direction_deadline_overdue`
- `verdict_non_compliant`
- `sample_deadline_approaching`
- `direction_deadline_approaching`
- `research_assigned`
- `sample_analyzed`
- `direction_registered`
- `research_completed`
- `protocol_ready`
- `direction_completed`
- `protocol_formable`

## Permissions And Scope Policy

Every operation checks:

1. Permission: role has action on resource.
2. Scope: target entity is visible to the user.

The backend must apply scope filters to list and read endpoints. Frontend-provided filters cannot widen access.

### Actions

CRUD actions:

- `create`
- `read`
- `update`
- `delete`

Domain actions:

- `import`
- `register`
- `reject`
- `confirm`
- `start`
- `result`
- `requeue`
- `close`
- `issue`
- `mark_read`
- `hide`

### Scope Types

- `global`: unrestricted.
- `own_branch`: records in the user's branch scope.
- `own_lab`: records in the user's lab scope.
- `own_objects`: records connected to the sanitary inspector's objects/directions.
- `own_alerts`: alerts where `alerts.user_id = current_user.id`.
- `entity_id`: history for a specific entity after access to that entity is allowed.

### Roles

- `developer`: global wildcard for development and test environments.
- `user_admin`: users, roles, permissions, and scopes only.
- `registrar`: registration workflow within own branch.
- `sanitary_inspector`: read-only access to own objects/directions and related protocols.
- `lab_doctor`: research and tests in own lab.
- `lab_assistant`: read-only access in own lab.
- `lab_chief`: lab doctor permissions plus sample closing and lab catalog management.
- `branch_chief`: read-only branch visibility and alerts.

### 404 And 403 Rule

- Return `404` if an entity exists but is outside user scope.
- Return `403` if the entity is in scope but the user lacks the action permission.

### Command Permission Examples

`POST /samples/{id}/reject`:

- Permission: `samples.reject`.
- Roles: `registrar`, `lab_doctor`, `lab_chief`.
- Scope:
  - Registrar: sample's direction belongs to registrar branch.
  - Lab doctor or lab chief: sample has research in user's lab.
- Status: `pending`.

`POST /samples/{id}/close`:

- Permission: `samples.close`.
- Roles: `lab_chief`.
- Scope: sample has research in chief's lab.
- Status: `analyzed`.

`POST /tests/{id}/complete`:

- Permission: `tests.result`.
- Roles: `lab_doctor`, `lab_chief`.
- Scope: `test.research.lab_id` is in user's lab scope.
- Status: `in_progress`.

## Audit

Every CRUD operation and every command writes `history`.

`history` fields:

- `id`
- `branch_id`
- `entity_type`
- `entity_id`
- `action`
- `actor_id`
- `actor_name`
- `snapshot`
- `diff`
- `created_at`

Actions:

- `CREATE`
- `UPDATE`
- `DELETE`
- `RESTORE`
- `STATUS_TRANSITION`

For status transitions:

```json
{
  "field": "status_id",
  "from_code": "ordered",
  "to_code": "in_progress",
  "entity_type": "research",
  "reason": "research_started",
  "triggered_by_role": "lab_doctor"
}
```

If one command changes multiple entities, write one history row per changed entity.

## Alerts

Alerts are created by system policy, not manually by users.

Fields:

- `id`
- `user_id`
- `branch_id`
- `entity_type`
- `entity_id`
- `type`
- `message`
- `is_read`
- `is_hidden`
- `created_at`

Normative alert types:

- `sample_rejected`
- `sample_deadline_overdue`
- `direction_deadline_overdue`
- `verdict_non_compliant`
- `sample_deadline_approaching`
- `direction_deadline_approaching`
- `research_assigned`
- `sample_analyzed`
- `direction_registered`
- `research_completed`
- `protocol_ready`
- `direction_completed`
- `protocol_formable`

Active alert query:

```sql
WHERE user_id = :current_user_id
  AND is_hidden = false
```

## Error Contract

All errors use problem-details style:

```json
{
  "type": "https://api.example.com/errors/invalid-status-transition",
  "title": "Conflict",
  "status": 409,
  "detail": "Sample can be closed only from analyzed status.",
  "instance": "/api/v1/samples/{id}/close",
  "errors": []
}
```

Validation errors include `errors`:

```json
{
  "type": "https://api.example.com/errors/validation",
  "title": "Validation failed",
  "status": 422,
  "detail": "Request validation failed",
  "instance": "/api/v1/directions/import",
  "errors": [
    {
      "type": "value_error",
      "loc": ["body", "samples", 0, "sample_type_id"],
      "msg": "Sample type is required",
      "input": null
    }
  ]
}
```

Status code rules:

- `400`: malformed request or invalid file syntax.
- `401`: unauthenticated.
- `403`: authenticated but action is not allowed.
- `404`: not found or outside scope.
- `409`: domain conflict, including invalid status transition.
- `422`: validation failed.
- `429`: rate limited.
- `500`, `502`, `503`: server or dependency failure.

Recommended domain error codes:

- `invalid_status_transition`
- `permission_denied`
- `entity_out_of_scope`
- `direction_not_editable`
- `sample_not_closeable`
- `sample_already_closed`
- `research_not_startable`
- `test_not_completable`
- `protocol_not_issuable`
- `import_file_invalid`
- `import_required_data_missing`

## Implementation Notes

- Never expose status lifecycle changes as plain `PATCH status_id` for workflow entities.
- Commands should be transactional for status changes and synchronous cascades.
- Alert creation can be asynchronous if the event is durable.
- Frontend should reread entity cards after commands using `GET` with `include`.
- `results` is not an MVP resource. Use `research` and `tests`.
- `directions.import_warnings` is used for MVP instead of a separate `import_issues` table.
- Keep status codes stable. UI logic and command validation should use codes, not localized names.
- Scope policy belongs on the backend. UI visibility is convenience only.
