# Real Notifications Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store real notifications in PostgreSQL, expose list/read/SSE APIs, and show live frontend toasts when SSE events arrive.

**Architecture:** The notifications context owns persistence, event-to-notification mapping, API schemas, and SSE formatting. Workflow command service forwards repository domain events to notifications after successful commands. The frontend composable owns loading, SSE connection, read state updates, and Nuxt UI toasts.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, PostgreSQL JSONB, Vue 3, Nuxt UI, EventSource.

---

### Task 1: Backend domain contract and repository

**Files:**
- Create: `backend/tests/contexts/notifications/test_notification_contract.py`
- Create: `backend/src/contexts/notifications/domain/contracts.py`
- Create: `backend/src/contexts/notifications/application/service.py`
- Create: `backend/src/contexts/notifications/infrastructure/repositories.py`
- Modify: `backend/src/infrastructure/db/models/entities.py`
- Modify: `backend/src/infrastructure/db/models/__init__.py`

- [ ] Write failing tests for event mapping, repository list filters, and `read_at`.
- [ ] Run targeted tests and confirm they fail because the implementation is missing.
- [ ] Add `Notification` ORM model and repository/service code.
- [ ] Run targeted tests and confirm they pass.

### Task 2: Backend API, SSE, and workflow integration

**Files:**
- Create: `backend/tests/contexts/notifications/test_notifications_api.py`
- Modify: `backend/src/contexts/notifications/presentation/router.py`
- Modify: `backend/src/contexts/laboratory_workflow/application/commands.py`
- Modify: `backend/src/contexts/laboratory_workflow/presentation/router.py`
- Create: `backend/migrations/versions/20260602_0012_notifications.py`

- [ ] Write failing API tests for `GET /alerts`, `POST /alerts/{id}/mark-read`, and SSE framing.
- [ ] Run targeted tests and confirm they fail because API returns stubs.
- [ ] Implement real routes, dependency wiring, and migration.
- [ ] Run targeted tests and confirm they pass.

### Task 3: Frontend real-time notifications

**Files:**
- Modify: `frontend/src/shared/types/index.ts`
- Modify: `frontend/src/shared/composables/useSystemNotifications.ts`
- Modify: `frontend/src/shared/ui/NotificationsSlideover.vue`
- Modify: `frontend/src/pages/DashboardPage.vue`

- [ ] Update notification type to UUID/string ids and `readAt`.
- [ ] Load real notifications from `/alerts`, connect `/alerts/stream`, show `useToast().add(...)` on new SSE notification.
- [ ] Add unread/read tabs and mark-read action in the slideover.
- [ ] Show unread count on the dashboard bell.

### Task 4: Verification

**Files:**
- Backend and frontend changed files.

- [ ] Run backend targeted tests for notifications.
- [ ] Run backend app/model smoke tests.
- [ ] Run frontend typecheck/lint/build as available.
- [ ] Report any blocked checks with exact command output.
