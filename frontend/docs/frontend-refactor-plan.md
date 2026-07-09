# Frontend — Detailed Refactor & Remediation Plan

**Goal (north star):** *reduce the amount of code so the system is easier to understand* — while fixing the correctness and security defects found in review. Every phase below is measured by net lines removed **and** comprehension gained (fewer concepts, fewer places to edit per change).

**Source reviews:** [`frontend-code-review.md`](./frontend-code-review.md) (whole app) · [`frontend-tables-code-review.md`](./frontend-tables-code-review.md) (table subsystem). Section references like *(app §3.1)* / *(tables §4.2)* point back to those.

**Date:** 2026-06-27 · **Stack:** Vue 3.5 · Nuxt UI 4 · Vite 8 · Pinia · vue-router 5 · vue-i18n 10 · Zod 4 · `@hey-api` SDK · Bun.

**Baseline verified today:** `mock-data.ts` (480 LOC) 0 importers · `CrudModulePage.vue` (540) unrouted, 6 type-only importers · no router guard (11 routes all `requiresAuth:false`) · no `getRowId` anywhere · raw `localStorage.` in 5 files · `JSON.parse(JSON.stringify)` in 11 sites/6 files · 8 test files, no `test` script · `typecheck` RED, `bun test` 42✓/1✗.

> All LOC deltas are estimates marked *(est.)*. They exist to keep the "less code" goal measurable, not as contractual numbers.

---

## 0. The reduction scoreboard (targets)

| Area | Now | Target | Δ (est.) | How |
|------|----:|-------:|-----:|-----|
| `mock-data.ts` | 480 | 0 | **−480** | delete (0 imports) |
| `CrudModulePage.vue` | 540 | ~25 (`.ts` type) | **−515** | delete body, extract type |
| localStorage wrappers (×5) | ~150 | ~35 | **−115** | one `useJsonStorage` on vueuse |
| deep-clone sites (×11) | ~11 | 1 helper | small LOC, big correctness | one `clone()` |
| `useTableSettings` + `useServerTable` persistence | 79 + ~55 | ~70 | **−64** | merge into one owner |
| `DictionaryCrudContent` + 4 page wrappers | ~1873 | ~720 | **−1150** | `CrudTableHost` + `workflow-commands.ts` + 1 page |
| `EntityDetailDialogBase` | 1115 | ~700 (split) | **−415** | tabs → children + composables |
| `UsersPage` | 748 | ~260 | **−490** | reuse `CrudTableHost` + `useUserForm` |
| `UserTypesPage` | 645 | ~320 | **−325** | `useRolesEditor` + primitives |
| **Net** | | | **≈ −3 500 LOC** | + real RBAC, + green CI |

Two things grow on purpose: **security code** (a guard + RBAC wiring, ~120 LOC) and **declarative config** (`workflow-commands.ts`). Both trade imperative sprawl for data — fewer concepts even where lines are added.

---

## 1. Guiding principles for the refactor

1. **Subtract before you restructure.** Delete dead code first so the decomposition operates on a smaller surface (Phase 2 precedes Phase 5).
2. **One concept, one home.** Each cross-cutting concern (storage, clone, settings, filters, status, workflow) gets exactly one module; all call sites import it.
3. **Push behavior into data.** Per-entity differences become entries in `crud-modules.ts` / `workflow-commands.ts`, not `if (presetKey === …)` branches in a god component (Open/Closed).
4. **Generic host, declarative pages.** Pages become ~15-line files: `<WorkflowCrudPage :config :workflow>`. Adding an entity = adding a config row, not editing a 1500-line SFC.
5. **Green baseline is a prerequisite, not a finale.** Phase 0 makes `typecheck`+`test` pass *first* so every later phase has a regression net.
6. **No behavior change in subtractive phases.** Phases 2–4 must leave the UI identical (verified by typecheck + tests + a manual smoke pass); only Phase 5 reshapes components and Phase 1/6 change behavior intentionally.

---

## 2. Phase map & dependencies

```
Phase 0  Safety net (green typecheck+test, wire `test` script)      ─┐ prerequisite for all
Phase 1  Security / RBAC enforcement      ── independent ───────────┤ (P0, can land first/parallel)
Phase 2  Delete dead code + relocate CrudModuleConfig type           │  needs P0 green
Phase 3  Unify infrastructure (storage / clone / settings / filters) │  needs P2 (fewer files)
Phase 4  Structural table bug fixes (getRowId, width, status, …)     │  needs P0
Phase 5  Decompose god components                                    │  needs P2+P3+P4
Phase 6  i18n + consistency + tooling hygiene                        ┘  needs P5 (final sweep)
```

Critical path for the *table* refactor the user is about to do: **0 → 2 → 3 → 4 → 5**. Security (1) and i18n/tooling (6) parallelize around it.

---

## 3. Phase 0 — Safety net: green the baselines *(P0, prerequisite, ~0.5 day)*

You cannot "reduce code with confidence" on a RED baseline — regressions hide. Make the gates pass and runnable first.

### 0.1 Fix the `UsersPage` broken toolbar *(tables §4.1, app §10.2)*
- **Files:** `modules/admin/pages/UsersPage.vue` (`:549`, `:688`, `:691`).
- **Change:** template binds undefined `refreshToken` and `crudContent?.columnMenuItems` (copy-paste from dictionary wrappers). Replace `@click="refreshToken++"` → `@click="table.refresh()"`; bind `:items="columnMenuItems"` (the local already exists at `:549`, currently unused). Delete the dead `crudContent` ref usage.
- **Impact:** fixes the refresh button + column menu (currently both dead); clears 3 TS errors. Net ~−2 LOC.
- **Verify:** `typecheck` loses TS2339×2 + TS6133×1; manual: refresh + column toggle work.

### 0.2 Remove `DirectionsPage` dead selection wiring *(tables §7, app §10.2)*
- **Files:** `pages/DirectionsPage.vue` (`:8`, `:27`, `:29`).
- **Change:** delete the unused `SelectionActionBar` import + `selectedCount`/`selectionActions` computeds (the bar is never rendered, unlike Research/Samples/Tests). *(This file disappears entirely in Phase 5; for now just green it.)*
- **Impact:** clears 3 TS6133 errors; net ~−15 LOC.

### 0.3 Wire and green the test suite *(app §10.1)*
- **Files:** `package.json` (scripts), `tests/shared/config/crud-modules.test.ts`, `shared/config/crud-modules.ts`.
- **Change:** add `"test": "bun test"`. Resolve the 1 failing test: `crud-modules.test.ts` expects `research.filterFields` to exclude `comment`/`recommendation`/`created_at` but the config includes them — **decide the source of truth** (likely the config is right; update the test) and align. Then `bun test` = all green.
- **Impact:** 0 LOC product code; turns an unrunnable suite into a real net.
- **Verify:** `bun run typecheck` exit 0 **and** `bun test` exit 0.

### 0.4 Make the gates real
- **Change:** add a CI step (or a `pre-push` note) running `lint && typecheck && test`. Guard `VueDevTools()` in `vite.config.ts` with `mode !== 'production'` *(app §10.3)*.
- **Exit criteria for Phase 0:** both gates green, `test` script present, devtools out of prod build.

---

## 4. Phase 1 — Security / RBAC enforcement *(P0, independent track, ~1 day)*

This is the highest-severity area (app §3) and is **independent of the table refactor** — schedule it first or in parallel. Today the UI gates nothing.

### 1.1 Add a navigation guard *(app §3.1)*
- **Files:** new `app/router/guard.ts`; `app/router/index.ts` (`registerGuard(router)`); `app/router/routes.ts` (set `requiresAuth` correctly per route — `true` for app screens, `false` for `/login` and error pages).
- **Change:** `router.beforeEach((to) => { if (to.meta.requiresAuth && !auth.isAuthenticated) return { name: 'login', query: { redirect: to.fullPath } } })`. Consume the `requiresAuth` meta that already exists (`vue-router.d.ts:12`) but is read by nothing.
- **Impact:** +~25 LOC; closes "every URL is public."

### 1.2 Bootstrap the session on boot *(app §3.2)*
- **Files:** `app/index.ts` (or the guard), `modules/auth/composables/useAuth.ts` (`restoreSession` at `:72`).
- **Change:** `await restoreSession()` once before mount (or a one-shot guard that hydrates then validates against the httpOnly cookie). Today `restoreSession` is called only in `UsersPage:626`, so reloads trust stale `useStorage("auth:user")` with no server check.
- **Impact:** +~10 LOC; forged/stale localStorage no longer looks logged-in.

### 1.3 Drive `can()` from backend permissions; default-deny *(app §3.3)*
- **Files:** `modules/auth/composables/useAuth.ts` (`effectivePermissions` `:29/:84`), `shared/config/user-modes.ts`.
- **Change:** `effectivePermissions` returns the backend `permissions` already fetched at login (currently stored then **ignored**), not `resolveModePermissions(activeModeId)`. Empty perms ⇒ deny. Gate the mode switcher (`setMode`, exposed in `UserMenu`) behind `import.meta.env.DEV` / admin-only, so users can't self-elevate from default `developer = *:*` (`user-modes.ts:222`).
- **Impact:** removes a whole "frontend preset" pathway; `permissions` state stops being dead (app §5). Net roughly flat, far fewer concepts.
- **Verify:** a non-admin user sees gated actions disabled; switching mode is unavailable in prod build.

### 1.4 Move auth state toward in-memory + cookie *(app §3.4, optional/stretch)*
- Prefer in-memory state hydrated by `restoreSession()` over `useStorage` for `user`/`permissions`/`mode` (XSS-readable, cross-tab stale). Lower priority than 1.1–1.3; bundle if time allows.

> **Note:** the memory record marks access control as *"frontend-first phase, non-enforcing by design."* Confirm with the team whether 1.1–1.3 are in scope now or deferred until the backend enforces. Either way, real enforcement must be backend-side; this phase only makes the **UI** stop lying about protection.

---

## 5. Phase 2 — Delete dead code + relocate the orphan type *(pure subtraction, ~0.5 day)*

Biggest comprehension win for the least risk: ~1 000 LOC vanish with zero behavior change.

### 2.1 Extract `CrudModuleConfig` to a real `.ts` module *(tables §3.2, app §7.4)*
- **Files:** new `shared/types/crud.ts`; update 6 importers — `shared/config/crud-modules.ts:1`, `modules/dictionaries/config.ts:1`, `modules/dictionaries/pages/DictionaryCrudContent.vue:14`, `shared/ui/BusinessEntityDetailModal.vue:2`, `shared/ui/DictionaryCrudDetailModal.vue:4`, `shared/ui/EntityDetailDialogBase.vue:4`.
- **Change:** move the `CrudModuleConfig`/`CrudColumn` type defs out of the page into `shared/types/crud.ts`; repoint imports. This is what keeps the dead page alive.
- **Impact:** +~25 LOC (the type file), unblocks 2.2. Inverted page→type dependency removed.

### 2.2 Delete `CrudModulePage.vue` body *(tables §3.1)*
- **Files:** delete `pages/CrudModulePage.vue` (540 LOC). Confirm no route refs (verified: none).
- **Impact:** **−540 LOC**; removes the second, dead table stack, its `window.confirm` (tables §4.7), `w-[${width}]` bug (§4.3), identical-branch ternary (§4.8), single-option page-size (§5.4), and the inline-filter UI divergence (§5.3) — all in one delete.

### 2.3 Delete `mock-data.ts` *(app §9)*
- **Files:** delete `shared/api/mock-data.ts` (480 LOC, 0 importers — verified).
- **Impact:** **−480 LOC**.

### 2.4 Remove no-ops *(tables §7, app §9)*
- `DictionariesPage.vue:82–84` empty `watch(moduleKey, () => {})`. (DirectionsPage dead wiring already cleared in 0.2.)
- **Exit criteria:** typecheck/test still green; grep shows no remaining import of deleted modules.

---

## 6. Phase 3 — Unify duplicated infrastructure *(dedup, ~1 day)*

Collapse each reimplemented concern to one module. Pure consolidation; behavior identical.

### 3.1 One JSON-localStorage helper *(app §7.1, tables §3.4)*
- **Files:** new `shared/composables/useJsonStorage.ts` (thin wrapper over vueuse `useStorage`, already a dep used in `useAuth`/`MainLayout`). Repoint the 5 raw users: `useTableSettings.ts`, `useAppearanceSettings.ts`, `useServerTable.ts`, `i18n/index.ts`, `tour/tour.storage.ts`.
- **Change:** delete the ≥4 near-identical `try/catch` read/write wrappers; one helper with typed `read<T>()/write<T>()`.
- **Impact:** **−~115 LOC**; one place to reason about persistence/serialization.

### 3.2 Merge the two table-settings systems *(tables §3.4)*
- **Files:** `useServerTable.ts:40–95` (private `loadTableSettings`/`persistTableSettings`) and `useTableSettings.ts:3–79` write the **same** `table-settings:…` key non-atomically (interleaving column-visibility and filter writes clobber each other).
- **Change:** make `useTableSettings` the sole owner of the whole `TableSettings` record (filters + sorting + pageSize + columnVisibility); `useServerTable` consumes it. One read-modify-write owner ⇒ no clobber.
- **Impact:** **−~64 LOC** + fixes a real data race.

### 3.3 One clone helper *(tables §6)*
- **Files:** new `shared/utils/clone.ts` (or export `cloneFilters` from `useServerTable.ts:35`). Repoint all 11 `JSON.parse(JSON.stringify(...))` sites (`CrudModulePage` removed in 2.2; remaining in `UsersPage:146/376`, `UserTypesPage:91/255`, `DictionaryCrudContent:212/220/757`, `useOptimistic.ts:3`).
- **Change:** one typed `clone<T>(v: T): T` (structuredClone-based) — preserves `Date`/`undefined`, faster, single concept.
- **Impact:** small LOC, removes a recurring footgun.

### 3.4 One filter component *(tables §5.3)*
- With `CrudModulePage`'s inline-grid filters gone (2.2), `CrudFilterModal` is the only filter UI left — confirm all pages use it; delete any now-unused inline filter bits. (Mostly realized by Phase 2.)

---

## 7. Phase 4 — Structural table bug fixes *(correctness, ~1 day)*

The deeper table bugs that survive deletion and must be fixed before/with decomposition.

### 4.1 Key row selection by id, not array index *(tables §4.2 — 🔴)*
- **Files:** `shared/ui/CrudDataTable.vue` (add `:get-row-id="(row) => row.id"` to `UTable`); selection readers `DictionaryCrudContent.vue:881`, `UsersPage.vue:446`.
- **Change:** stop mapping `rowSelection` keys through `table.data.value[Number(k)]`; key by `row.id`. Index keys corrupt under infinite-scroll append / optimistic `unshift`/`filter`, so bulk delete/register/reject can hit the wrong records.
- **Impact:** ~flat LOC; eliminates a data-corruption class. **Add a regression test.**

### 4.2 Fix column widths *(tables §4.3)*
- **Files:** `CrudDataTable.vue` cell/header (the surviving `w-[${column.width}]` after `CrudModulePage` deletion).
- **Change:** Tailwind JIT can't see interpolated classes — use inline `:style="{ width }"` (or a safelisted token set). (No config sets `width` today, so this also re-enables an unused feature cleanly.)

### 4.3 Remove the dead status-cell branch *(tables §4.4)*
- **Files:** `DictionaryCrudContent.vue` (`h(UBadge,…)` in `cell()` at `:721` vs the `#status-cell` slot at `:1394`). The named slot wins, so the render-function branch is dead. Keep the slot, delete the branch. *(Largely absorbed by Phase 5's status work.)*

### 4.4 Scope the IntersectionObserver + debounce the MutationObserver *(tables §4.6, §8)*
- **Files:** `CrudTableShell.vue:37` (`document.querySelector("tbody")` fallback can bind to another table/modal → spurious `loadMore`) and `:73` (re-queues on every subtree mutation, incl. per-cell skeleton swaps).
- **Change:** strictly scope to `sectionRef`; debounce/observe only `tbody` row-count.

### 4.5 Honest delete/undo *(tables §4.5)*
- **Files:** `DictionaryCrudContent.vue:142–157`, `UsersPage.vue:55–69`.
- **Change:** undo currently POSTs a *new* record (new id) — not a restore; and bulk delete has no undo. Prefer a real soft-delete/restore endpoint, or drop the undo illusion and make single+bulk consistent. *(Coordinate with backend; may defer.)*

---

## 8. Phase 5 — Decompose the god components *(the main restructure, ~3–4 days)*

This is where the bulk of the −LOC and the comprehension gain land. Order: build the generic host + registries, then migrate pages onto them, then delete the god component.

### 5.1 Target architecture for the dictionary/workflow tables

**New modules (the absorbers):**
| New file | Role | est. LOC |
|----------|------|----:|
| `shared/ui/CrudTableHost.vue` | Generic table host: `CrudDataTable` + filters + CRUD (create/update/delete/optimistic/undo) + id-keyed selection. **No domain knowledge.** Props: `config`; slots for cells/actions; emits selection. | ~300 |
| `shared/config/workflow-commands.ts` | Declarative registry keyed by `resource` → `WorkflowCommand[]` (`{ id, labelKey, icon, appliesTo(status), can(perm), run(selection) }`). Replaces the 11 hardcoded `workflowCommands` (`:489–678`) + 11 `can*Selected*` computeds + 11 `*Selected*` wrappers. | ~200 (data) |
| `shared/domain/status.ts` | Status from backend `status.code` enum (typed map). Replaces brittle `normalizeStatusCode` substring heuristics (`:426`, tables §5.2). | ~40 |
| `shared/ui/WorkflowCrudPage.vue` | The page wrapper: `UDashboardPanel` + toolbar + `CrudTableHost` + `SelectionActionBar` driven by `workflow-commands`. | ~120 |

**Pages collapse to ~15 lines each:**
```vue
<!-- pages/DirectionsPage.vue (and Research/Samples/Tests) -->
<script setup lang="ts">
import WorkflowCrudPage from '@/shared/ui/WorkflowCrudPage.vue'
import { directionsConfig } from '@/shared/config/crud-modules'
</script>
<template><WorkflowCrudPage :config="directionsConfig" resource="directions" /></template>
```

**Net:** `DictionaryCrudContent` (1473) + 4 wrappers (~400) ⇒ `CrudTableHost` (~300) + `workflow-commands.ts` (~200) + `WorkflowCrudPage` (~120) + `status.ts` (~40) + 4 trivial pages (~60) ≈ **~720 LOC (−1 150 est.)**, and the 28-member `defineExpose` template-ref contract (`:1265–1297`) disappears.

**Migration steps (incremental, keep green):**
1. Build `status.ts`, `workflow-commands.ts`, `CrudTableHost.vue` alongside the existing god component (no wiring yet).
2. Port **one** entity (Directions) to `WorkflowCrudPage`; verify parity (list, filter, CRUD, each workflow action, selection, detail dialog).
3. Port Research, Samples, Tests one at a time.
4. Delete `DictionaryCrudContent.vue` and the old per-page boilerplate once all four are migrated.

### 5.2 Decompose `EntityDetailDialogBase.vue` (1115) *(app §6)*
- **Files:** new `EntityDetailDialog.vue` (shell + tabs ~150) + `CardTab`/`TechnicalTab`/`RelatedTab`/`NotesTab` children + `useEntityDetail(kind,id)` (fetch) + `useRelatedEntities` (pagination) composables.
- **Change:** lift the 4 tabs, audit timeline, related pagination, inline edit, fullscreen out of one SFC; replace the hardcoded `EntityKind` union with config-driven kinds. **Est. −415 LOC** and each unit is independently readable.

### 5.3 Decompose `UsersPage.vue` (748) → reuse the host *(app §6)*
- **Files:** `useUsersTable` + `useUserForm` composables; render via `CrudTableHost` (now that selection/CRUD are generic). Users becomes config + a small page like the others. **Est. −490 LOC.**

### 5.4 Decompose `UserTypesPage.vue` (645) *(app §6)*
- **Files:** `useRolesEditor` composable + shared form primitives; reuse `CrudTableHost` where applicable. **Est. −325 LOC.**

---

## 9. Phase 6 — i18n, consistency & tooling hygiene *(final sweep, ~1–1.5 days)*

### 6.1 i18n pass over tables/modals/forms *(app §7.2, tables §5.1)*
- Route every hardcoded Russian literal in `CrudDataTable`/`CrudFormModal`/`CrudFilterModal`, empty/loading states, toasts, confirm copy, `"Да"/"Нет"` badges, and select-all aria-labels through `t()`. The `en` locale is fully wired (`fallbackLocale:'en'`), so these are an actual `en`-breakage, not polish. Add the keys to both `ru` + `en` in `messages.ts`.

### 6.2 Standardize forms on Zod *(app §7.3)*
- Replace `CrudFormModal`'s native `form.reportValidity()` + `Record<string,any>` state with a Zod schema per config (Zod already used in `LoginPage`). One validation paradigm; typed form state.

### 6.3 Cross-cutting polish
- `me()` request waterfall → parallelize or embed permissions backend-side *(app §4)*.
- `auth.api.ts` stop fabricating `email`/`department` — make optional/absent *(app §4.1)*.
- `useSystemNotifications` reset module-singleton (`eventSource`/`initialized`) on `clearSession` + add `onUnmounted` teardown *(app §8)*.
- `App.vue` scope context-menu suppression to table rows, not `document` (capture phase kills right-click app-wide) *(app §11)*.
- `MainLayout` cookie-consent toast → `onMounted`; fix leftover template "Documentation" URL *(app §11)*.
- `CrudSearchControl` drop mount autofocus *(tables §9)*.

---

## 10. New shared modules created by this plan (the "absorbers")

| Module | Replaces | Phase |
|--------|----------|------|
| `shared/types/crud.ts` | type stranded in `CrudModulePage.vue` | 2.1 |
| `shared/composables/useJsonStorage.ts` | ≥4 localStorage try/catch wrappers | 3.1 |
| `shared/utils/clone.ts` | 11 `JSON.parse(JSON.stringify)` sites | 3.3 |
| `shared/domain/status.ts` | `normalizeStatusCode` substring heuristics | 5.1 |
| `shared/config/workflow-commands.ts` | 11 hardcoded transitions + 22 computeds/wrappers | 5.1 |
| `shared/ui/CrudTableHost.vue` | generic half of `DictionaryCrudContent` | 5.1 |
| `shared/ui/WorkflowCrudPage.vue` | 4 copy-pasted page wrappers | 5.1 |
| `app/router/guard.ts` | the absent navigation guard | 1.1 |

Net module count rises slightly; **net concept count falls** — each cross-cutting idea has exactly one home.

---

## 11. Verification protocol (run after every phase)

1. `bun run typecheck` → exit 0 (gate; the only thing that catches undefined template refs since lint sets `no-undef:off` for `.vue`).
2. `bun test` → all green (add tests for 4.1 id-selection and 5.1 workflow-command gating).
3. `bun run lint` → clean.
4. **Manual smoke** (subtractive phases must show *no* visible change): load each table, filter, sort, infinite-scroll, create/edit/delete, run one workflow action per entity, open a detail dialog, toggle columns, switch `ru`/`en`.
5. For Phase 1: verify a logged-out user is redirected from a protected URL; a low-permission user sees gated actions disabled; mode switcher absent in prod build.

---

## 12. Risk register & rollback

| Risk | Mitigation |
|------|-----------|
| Decomposition (Phase 5) silently changes behavior | Migrate **one entity at a time**, parity-check against the still-present god component before deleting it. |
| id-selection change (4.1) breaks bulk actions | Land behind tests first; verify each bulk op against known ids. |
| Security guard (1.1) locks out during dev | `requiresAuth:false` on login/error; `redirect` query preserves deep links; feature-flag if the team wants frontend-first deferred. |
| Settings-merge (3.2) loses persisted prefs | One-time migration read of both old shapes; keep the same `table-settings:` key. |
| "Reduce LOC" tempts premature deletion of used code | Every deletion preceded by a grep for importers (done for 2.2/2.3; repeat per file). |
| `crud-modules` test/config drift hides a real spec | In 0.3 decide source of truth explicitly with the domain owner, don't just match the test to the code. |

**Rollback:** each phase is an independent, revertable changeset; Phases 2–4 are behavior-preserving so reverting is safe; Phase 5 is per-entity, so a bad migration reverts one entity, not the suite.

---

## 13. Suggested sequencing

| Order | Phase | Why here | Est. |
|------:|-------|----------|-----|
| 1 | **0 Safety net** | green baseline before touching anything | 0.5 d |
| 2 | **1 Security** (parallel track) | P0, independent of tables | 1 d |
| 3 | **2 Delete dead code** | −1 000 LOC, zero risk, shrinks surface | 0.5 d |
| 4 | **3 Unify infra** | dedup the primitives the host will use | 1 d |
| 5 | **4 Table bug fixes** | correctness before decomposition | 1 d |
| 6 | **5 Decompose god components** | the main −LOC + comprehension payoff | 3–4 d |
| 7 | **6 i18n + polish + tooling** | final consistency sweep | 1–1.5 d |

**Total ≈ 8–10 working days**, delivering **≈ −3 500 LOC**, real RBAC enforcement, green/wired CI gates, and a table layer where adding an entity is a config row rather than a god-component edit.

---

*Grounding: anchors re-verified against current `src` on 2026-06-27 (dead-code import counts, route guard absence, `getRowId` absence, localStorage/clone duplication counts, test wiring). Full findings in [`frontend-code-review.md`](./frontend-code-review.md) and [`frontend-tables-code-review.md`](./frontend-tables-code-review.md).*
