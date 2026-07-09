# Frontend — Full Code Review

**Scope:** The entire `bio` frontend (`frontend/src`) — app shell, routing, auth/access, API layer, state, modules, shared composables/UI, build tooling.
**Stack:** Vue 3.5 · Nuxt UI 4 · Vite 8 · Pinia · vue-router 5 · vue-i18n 10 · Zod 4 · `@hey-api` generated SDK · Bun.
**Date:** 2026-06-27

> **Companion document:** the table subsystem (`CrudDataTable`, `CrudTableShell`, `useServerTable`, `DictionaryCrudContent`, `crud-modules`, the per-entity pages, etc.) is reviewed separately and in depth in **[`frontend-tables-code-review.md`](./frontend-tables-code-review.md)**. This document covers everything else and only summarizes table findings where they intersect app-wide concerns.

Severity: 🔴 Critical · 🟠 High · 🟡 Medium · 🔵 Low.

---

## 1. Executive summary

The app is a well-structured Vue 3 LIMS with a genuinely good API abstraction, FSD-style layering, i18n/SSE/optimistic-update infrastructure, and unit-tested pure utilities. The problems cluster in four areas:

1. **🔴 Access control is non-enforcing.** There is **no router navigation guard**, every route is `requiresAuth: false`, the session is **never re-validated on boot**, and `can()` reads a **localStorage-stored, user-switchable frontend preset** (defaulting to `developer` = full access) instead of the backend permissions it already fetches. As shipped, the UI gates nothing.
2. **🟠 A few oversized "god" components** (`DictionaryCrudContent` 1473, `EntityDetailDialogBase` 1115, `UsersPage` 748, `UserTypesPage` 645) concentrate data + permissions + forms + domain workflow.
3. **🟠 Cross-cutting duplication & inconsistency:** localStorage persistence reimplemented ≥4×, two validation paradigms, and hardcoded Russian strings that break the (fully wired) `en` locale.
4. **🟡 Tooling gaps:** an 8-file test suite that isn't wired into `package.json` and is currently **RED**, `typecheck` currently **RED**, devtools shipped in prod build, and ~1 000 lines of dead code.

---

## 2. Architecture & project structure

**Layout** (`app/` shell · `modules/<feature>/` · `shared/` · `pages/`) is a sensible feature-sliced layout. Good.

- 🟡 **`pages/` vs `modules/.../pages/` split is inconsistent.** Some routed pages live in `src/pages/` (Directions, Research, Samples, Tests, Dashboard, Login…), others in `src/modules/<x>/pages/` (UsersPage, UserTypesPage, DictionariesPage, DictionaryCrudContent). Pick one convention (routed screens in `pages/`, feature internals in `modules/`).
- 🟡 **`routes.ts` has two separate `/` → `MainLayout` route blocks** (`:16–31` and `:33–84`) that could be one. Dashboard is split from the other authed pages for no functional reason.
- 🔵 `App.vue` wraps `<RouterView>` in `<Suspense>` with **no fallback slot** — a slow async layout shows nothing rather than a loader.

---

## 3. 🔴 Security & access control

This is the headline area. Each item below is independently verifiable.

### 3.1 🔴 No navigation guard; every route is public
`app/router/index.ts` creates the router with **no `beforeEach`** (verified — no guard anywhere in `src`). Every route in `routes.ts` is `meta: { requiresAuth: false }`, including `/access/users` and `/access/roles`. The `requiresAuth` meta type exists (`app/router/vue-router.d.ts:12`) but **nothing consumes it**. Any URL is directly reachable regardless of auth state; the sidebar only `disabled`s links cosmetically (`MainLayout.vue`), which does not stop direct navigation.

### 3.2 🔴 Session is never bootstrapped / re-validated
`restoreSession()` exists (`useAuth.ts:72`) but is called in exactly **one** place — `UsersPage.vue:626`, after editing your own user. It is **not** called on app start (`app/index.ts` only registers an `onUnauthorized → logoutLocal` hook). Because `user` is persisted via `useStorage("auth:user")`, `isAuthenticated` stays `true` across reloads **with zero server verification**; a stale/forged localStorage entry looks logged-in until the first API call happens to 401.

### 3.3 🔴 `can()` is a self-elevatable frontend preset, not real RBAC
`useAuth.can()` → `effectivePermissions` → `resolveModePermissions(activeModeId)` (`useAuth.ts:29,84`). That is the **frontend preset** in `user-modes.ts`, **not** the backend permissions, which *are* fetched at login and stored in `permissions` but then ignored (acknowledged in the `:18–21` comment). Consequences:
- `defaultUserModeId = "developer"` (`user-modes.ts:222`) grants `{ resource: "*", action: "*" }` — **full access is the default**.
- `activeModeId` is `useStorage("auth:mode")` and `setMode()` is exposed to the UI (`UserMenu`), so a user can **switch their own role/permissions** client-side.

This is fine *only* if the backend independently enforces every operation. The refactor must: (a) drive `can()` from `auth.effectivePermissions` = backend `permissions`, (b) restrict the mode switcher to a dev/admin build flag, and (c) add a real route guard.

### 3.4 🟡 Auth state in localStorage
`user`/`permissions`/`mode` use `useStorage` (localStorage). Readable by any XSS and survives "logout" on other tabs until cleared. Prefer in-memory state hydrated from `restoreSession()` against the httpOnly cookie the client already sends (`credentials: "include"`).

---

## 4. API layer — `shared/api/client.api.ts` (mostly strong)

**Good:** single typed `apiRequest`, snake_case request/response conversion, robust `getErrorMessage` (handles `detail[]`/`message`/`title`), `meta` normalization, `401/403` hooks, cursor auto-paging for reference options, FormData upload path. This is the best-engineered part of the codebase — keep it as the model.

- 🟡 **`me()` is a request waterfall** (`auth.api.ts:144–159`): `/auth/login`-style `/auth/me` then a sequential `/user/me/permissions`. Parallelize or have the backend embed permissions.
- 🟡 **`normalizeQueryParams` silently drops `offset`** (`client.api.ts:143`). Combined with `useServerTable.buildParams` never emitting `page`/`offset`, the (dead) paginated `CrudModulePage` could never actually page the server — another reason it's non-functional. Make offset/cursor handling explicit.
- 🔵 **Module-load side effect:** `generatedApiClient.setConfig(...)` runs at import time (`:44`). Works, but couples config to import order and complicates testing; consider an explicit `configureApiClient()` called from `app/index.ts`.
- 🔵 `apiDeleteRequest`/`apiCommandRequest` are defined but lightly used; fine.

### 4.1 🟡 Hand-maintained backend↔frontend mapping
`auth.api.ts` keeps `knownResources`, `knownActions`, `mapResource`, `mapAction` by hand and **fabricates fields**: `email: \`${username}@local\`` (`:113`) and `department: { id:null, name:null }` (`:116`). Fake data flowing into the `AuthUser` type is a trap for any feature that trusts `user.email`. Either extend the backend contract or make these fields optional/absent rather than synthesized.

---

## 5. State management

- ✅ Pinia setup-store `useAuth` is clean and cohesive.
- 🟡 `logoutLocal` is just an alias of `clearSession` (`useAuth.ts:104`) — two public names for one behavior; pick one.
- 🟡 `permissions` is stored but unused by `can()` (§3.3) — dead state until RBAC is wired.

---

## 6. God components (see also tables doc)

| File | LOC | Concern |
|------|----:|---------|
| `modules/dictionaries/pages/DictionaryCrudContent.vue` | 1473 | Generic CRUD + 11 hardcoded entity workflows + 28-member `defineExpose` — see tables review §3.3 |
| `shared/ui/EntityDetailDialogBase.vue` | 1115 | Business-entity detail: 4 tabs (card/technical/related/notes), audit timeline, related-entity pagination, inline edit, fullscreen — all in one SFC. Hardcoded `EntityKind` union; imports `CrudModuleConfig` from the dead page (§9). |
| `modules/admin/pages/UsersPage.vue` | 748 | Users table + permission/override loading + form state + column model in one component |
| `modules/user-types/pages/UserTypesPage.vue` | 645 | Roles/permissions editor (not yet read in depth — flag for same decomposition) |

🟠 **Recommendation:** extract data-fetching into composables (`useUserForm`, `useEntityDetail`), move presentational pieces into child components, and lift domain config out of SFCs. The reusable primitives already exist (`CrudDataTable`, `CrudFormModal`) — the god components predate/ignore them.

---

## 7. Cross-cutting duplication & inconsistency

### 7.1 🟠 localStorage persistence reimplemented ≥4×
Near-identical `try/catch` read/write wrappers appear in `useServerTable.ts` (`:50–95`), `useTableSettings.ts` (`:10–34`), `useAppearanceSettings.ts` (`:56–77`), and the tour storage — **while `@vueuse/core`'s `useStorage` is already a dependency** and used in `useAuth`/`MainLayout`. Collapse to one `useStorage`-based helper (or a single `safeJsonStorage`). See tables doc §3.4 for the two settings systems that even share a key.

### 7.2 🟠 i18n is fully bilingual but tables/modals/forms hardcode Russian
`shared/i18n/` wires **ru + en** (`messages.ts` has both; `index.ts` resolves/persists locale, sets `fallbackLocale: "en"`, syncs `<html lang>`). Yet `CrudDataTable`, `CrudFormModal`, `CrudFilterModal`, the empty/loading states, all toasts, confirm copy, and `"Да"/"Нет"` badges are **hardcoded Russian literals** — so switching to `en` leaves large parts of the UI in Russian. This is a correctness bug for the `en` locale, not just polish. Route table/modal/form strings through `t()`.

### 7.3 🟡 Two validation paradigms
`LoginPage.vue` uses a proper **Zod** schema (`:44–61`); `CrudFormModal.vue` uses native `form.reportValidity()` with no schema (`:84`) and a `Record<string, any>` form state (`:24`, eslint-disabled). Inconsistent UX and no shared validation contract despite Zod being a dependency. Standardize on Zod-driven forms.

### 7.4 🟡 `CrudModuleConfig` type lives in a dead `.vue` page
Imported by 6 modules from `@/pages/CrudModulePage.vue` (config, `DictionaryCrudContent`, `EntityDetailDialogBase`, 2 detail modals). Move to `shared/types/crud.ts` (also in tables doc §3.2).

---

## 8. Notifications / SSE — `useSystemNotifications.ts`

Good idea (SSE stream + toast + unread/read split), but:
- 🟠 **Module-level singleton state** (`notifications`, `eventSource`, `initialized`) never resets. `initialized` (`:25`) stays `true` and `eventSource` stays open across **logout/login**, so a second user inherits the first user's notifications and stream. Reset on `clearSession`.
- 🟡 **No teardown:** `EventSource` is closed only in `onerror` (`:102`), never on `onUnmounted`; the 3 s reconnect timer can leak. Return a cleanup and clear the timer.
- 🔵 `mapNotification` fabricates a `sender` object (`:53`) to satisfy a UI type — same "fake data" smell as §4.1.

---

## 9. Dead code

- 🟠 **`shared/api/mock-data.ts` (480 LOC)** — **zero imports** anywhere. Delete.
- 🟠 **`pages/CrudModulePage.vue` (540 LOC)** — unrouted; kept alive only for its exported type (tables doc §3.1).
- 🟡 `DictionariesPage.vue:82–84` empty `watch` no-op; `DirectionsPage` unused `SelectionActionBar`/`selectionActions` (tables doc §7).
- Total ≈ **1 000+ lines** of removable code.

---

## 10. Build, tooling & tests

### 10.1 🟠 Test suite exists, isn't wired in, and is RED
`tests/` has **8 `bun:test` files** covering pure utils (date-range, filter-select, form-layout, technical-audit, timeline-stepper, reference-options, use-server-table, crud-modules). But:
- `package.json` has **no `test` script** (and no CI config in repo) — they only run if someone happens to type `bun test`.
- Running them: **42 pass / 1 fail** — `crud-modules.test.ts` expects the `research` module's `filterFields` not to include `comment`/`recommendation`/`created_at`, but the config now does. The config drifted from its spec (or vice-versa). Decide which is correct and fix; then add `"test": "bun test"` and gate CI on it.

### 10.2 🟠 `typecheck` is currently RED
`bun run typecheck` (`vue-tsc`) fails — see tables doc Appendix (broken Users toolbar refs, dead DirectionsPage selection wiring). Since lint sets **`no-undef: off` for `.vue`** (`eslint.config.ts`), those undefined template references are caught *only* by `vue-tsc` — so typecheck must stay a required CI gate.

### 10.3 🟡 Vite/devtools/PWA
- `vite.config.ts` adds `VueDevTools()` **unconditionally** — it ships in the production build. Guard with `mode !== 'production'`.
- The entire `VitePWA` block is commented out though `vite-plugin-pwa` is a dependency and the app brands itself "Biologic-LIMS". Decide: enable or remove plugin + dep.
- Primary/neutral colors are inline in `vite.config`; fine, just note it's the theme source of truth.

### 10.4 🔵 Config hygiene
`tsconfig.app.json` is strong (`strict`, `noUnusedLocals/Parameters`, `noFallthroughCasesInSwitch`). `eslint.config.ts` is minimal — consider enabling `eslint-plugin-vue` template-expression rules so undefined refs fail lint too.

---

## 11. Accessibility & UX

- 🟠 **`App.vue` disables the native context menu globally** (`:11–21`, capture phase) to power the custom `RowContextMenu`. This kills right-click **everywhere** in the app (copy/paste menus, spellcheck, browser inspect). Scope it to table rows instead of `document`.
- 🟡 `MainLayout.vue` runs the **cookie-consent toast in setup body** (`:164–186`) rather than `onMounted`, so it executes during component setup on every mount; move to a lifecycle hook and gate on route.
- 🟡 External "Documentation" nav link points to `https://github.com/nuxt-ui-templates/dashboard-vue` (`MainLayout.vue:135`) — leftover template URL.
- 🔵 `CrudSearchControl` autofocus steals focus on every table page (tables doc §9); select-all aria-labels hardcoded RU.

---

## 12. Type safety (generally good)

- ✅ Only **7** non-generated `: any`/`as any` occurrences; one documented eslint-disable in `CrudFormModal`. `strict` on.
- 🟡 The boundary types lose information: `CrudRow = { id; [key: string]: unknown }`, `column.body?: (row: Record<string, any>)`, fabricated `AuthUser` fields. Tighten where entities are known.

---

## 13. What's good (preserve)

- **API layer** (`client.api.ts`): typed envelopes, case conversion, error normalization, 401/403 hooks, cursor paging — exemplary.
- **i18n infrastructure**: locale resolution/persistence, Nuxt UI + date-fns + Intl locale wiring, `<html lang>` sync.
- **Auth store** shape, **Zod** login validation, **SSE** notifications, **optimistic updates**, **skeleton** loading UX, **appearance settings**, **tours**.
- **Unit tests** for pure logic already exist — just wire and green them.
- Clean FSD-ish layering and the reusable `CrudDataTable`/`CrudFormModal` primitives.

---

## 14. Prioritized roadmap

**P0 — Security (do before anything ships as "access-controlled"):**
1. Add a `router.beforeEach` guard honoring `requiresAuth`; call `restoreSession()` on boot (§3.1/3.2).
2. Make `can()` read backend `permissions`; default-deny; gate the mode switcher behind dev/admin (§3.3).

**P1 — Correctness / red baselines:**
3. Fix the broken `UsersPage` toolbar + green `typecheck` (tables doc Appendix).
4. Wire `"test": "bun test"`, fix the failing `crud-modules` test, add CI gating typecheck + lint + test (§10.1/10.2).

**P2 — Dead code & duplication:**
5. Delete `mock-data.ts` and the `CrudModulePage` body; move `CrudModuleConfig` to `shared/types/` (§9, §7.4).
6. Unify localStorage persistence on `useStorage` (§7.1).
7. i18n pass over tables/modals/forms (§7.2).

**P3 — Decomposition (aligns with the tables refactor):**
8. Break up `DictionaryCrudContent`, `EntityDetailDialogBase`, `UsersPage`, `UserTypesPage` into composables + child components; standardize forms on Zod (§6, §7.3).
9. Notifications lifecycle/reset; scope context-menu suppression (§8, §11).

---

*Grounding: findings verified by reading the files cited, plus `bun run typecheck` (RED — see tables doc) and `bun test` (42 pass / 1 fail). The table subsystem is covered in [`frontend-tables-code-review.md`](./frontend-tables-code-review.md).*
