# Frontend Tables — Detailed Code Review

**Scope:** Table subsystem of the `bio` frontend (Vue 3 + Nuxt UI 4 + `@tanstack/table-core` + Vite).
**Goal:** Map the current table architecture and surface every problem worth fixing before the planned refactor.
**Date:** 2026-06-27

---

## 1. Files in scope

| Layer | File | LOC | Role |
|-------|------|----:|------|
| Composable | `shared/composables/useServerTable.ts` | 394 | Server-side data/filter/sort/cursor engine |
| Composable | `shared/composables/useTableSettings.ts` | 79 | localStorage column-visibility / settings |
| Primitive | `shared/ui/CrudDataTable.vue` | 203 | Reusable infinite-scroll `UTable` wrapper |
| Primitive | `shared/ui/CrudTableShell.vue` | 115 | Scroll/pagination shell + IntersectionObserver |
| Primitive | `shared/ui/table.ts` | 49 | Table `ui` preset, skeleton helpers |
| Primitive | `shared/ui/table-actions.ts` | 72 | `createActionColumn` factory |
| Primitive | `shared/ui/CrudTableLoadingRows.vue` / `CrudTableEmptyState.vue` | 67 / 72 | Loading & empty states |
| Filters | `CrudFilterModal/Controls/SearchControl/DateRangeFilter.vue` | 46–149 | Filter UI |
| Types | `shared/types/table.ts` | 24 | Column / filter types |
| Config | `shared/config/crud-modules.ts` | 798 | 18 entity table definitions |
| **God component** | `modules/dictionaries/pages/DictionaryCrudContent.vue` | **1473** | Infinite-scroll CRUD + workflow for 4 entities |
| **Dead page** | `pages/CrudModulePage.vue` | 540 | Paginated CRUD table (not routed) |
| Page | `modules/admin/pages/UsersPage.vue` | 748 | Users table |
| Page wrappers | `DirectionsPage/ResearchPage/SamplesPage/TestsPage.vue` | ~100 each | Thin wrappers over `DictionaryCrudContent` |
| Page | `DictionariesPage.vue` | 146 | Dictionary router shell |

Severity legend: 🔴 Critical (bug / data corruption) · 🟠 High (architecture / maintainability) · 🟡 Medium · 🔵 Low / polish.

---

## 2. Executive summary

The table layer works but is carrying **two competing implementations, one of which is dead**, plus a **1473-line god component** that fuses generic table mechanics with hard-coded per-entity business workflow. The biggest wins from the refactor are:

1. **Delete the dead paginated stack** (`CrudModulePage.vue`) and relocate the `CrudModuleConfig` type it accidentally owns.
2. **Split `DictionaryCrudContent.vue`** into a generic table host + per-entity workflow/config so adding an entity stops meaning "edit a 1500-line file."
3. **Fix the real bugs**: broken Users toolbar, index-based row selection, non-functional Tailwind width classes, dead status-cell branch.
4. **Unify** the two settings-persistence systems, the two filter UIs, and the hard-coded Russian strings (i18n already exists in the app).

---

## 3. Architecture-level findings

### 3.1 🟠 Two divergent table stacks; the paginated one is dead code
- **Infinite stack:** `CrudDataTable` → `CrudTableShell` (IntersectionObserver, `loadMore`, selection, slots). Used by `DictionaryCrudContent.vue` and `UsersPage.vue`.
- **Paginated stack:** `CrudModulePage.vue` renders `UTable` + `UPagination` directly, with its own column builder, inline filters and `window.confirm`.

`CrudModulePage.vue` **is never routed** (`app/router/routes.ts` has no reference). The only imports of it are `import type { CrudModuleConfig }` (config, 4 modals, `DictionaryCrudContent`). So ~540 lines of an alternative table implementation are shipped but unreachable, and they still contain their own bugs (see §4). **Recommendation:** delete the component body; extract `CrudModuleConfig` to `shared/types/crud.ts`.

### 3.2 🟠 `CrudModuleConfig` type lives inside an unused `.vue` page
`crud-modules.ts:1`, `BusinessEntityDetailModal.vue:2`, `DictionaryCrudDetailModal.vue:4`, `EntityDetailDialogBase.vue:4`, `DictionaryCrudContent.vue:14` all do `import type { CrudModuleConfig } from "@/pages/CrudModulePage.vue"`. Importing a core domain type from a page component is an inverted dependency and forces the whole SFC into the type graph. Move it to a plain `.ts` module.

### 3.3 🟠 `DictionaryCrudContent.vue` is a god component (1473 LOC)
Despite its "dictionary" name it contains:
- Generic CRUD (create/update/delete, optimistic, undo).
- A hard-coded `workflowCommands` table of **11 entity-specific state transitions** for directions/samples/research/tests (`:489–678`).
- 11 `can*Selected*` computeds (`:914–924`) + 11 thin `*Selected*` wrappers (`:1083–1114`).
- Per-entity branching by `presetKey` string in `isDeleteAllowed`, `deleteRestriction`, `rendersStatusBadge`, `resolveDetailKind`, `createDisabled`.
- A **28-member `defineExpose`** (`:1265–1297`) that the 4 page wrappers reach into via template refs.

This violates SRP and Open/Closed: adding an entity means editing this file in ~6 places, and the parent/child contract is the entire internal surface. **Recommendation:** extract (a) a generic `<CrudTableHost>` that owns table+filters+CRUD, (b) a `workflow-commands.ts` registry keyed by resource, (c) per-page composables (`useDirectionsWorkflow`, …) instead of one mega-component + `defineExpose`.

### 3.4 🟠 Duplicate settings-persistence systems
Two independent implementations of the **same** `TableSettings` shape and the **same** localStorage keys:
- `useServerTable.ts:40–95` — private `loadTableSettings`/`persistTableSettings` (persists `filters`, `sorting`, `pageSize`).
- `useTableSettings.ts:3–79` — `readSettings`/`writeSettings` + `useTableColumnVisibility` (persists `columnVisibility`).

Both read-modify-write the same key (`table-settings:…`) from different modules with non-atomic `{...current, ...patch}` merges, so a column-visibility write and a filter write that interleave can clobber each other. Consolidate into one `useTableSettings` owning the whole record.

### 3.5 🟠 Page-wrapper boilerplate is copy-pasted 4×
`DirectionsPage`, `ResearchPage`, `SamplesPage`, `TestsPage` are ~100 lines each of nearly identical `UDashboardPanel`/`UDashboardNavbar`/`UDashboardToolbar` + `CrudSearchControl` + `CrudFilterControls` + `SelectionActionBar`, differing only in `config` and the `selectionActions` array. The only real variation (the workflow actions) is already data in `DictionaryCrudContent`. This should collapse to one `<WorkflowCrudPage :config :actions>` wrapper.

---

## 4. Correctness bugs

### 4.1 🔴 `UsersPage.vue` toolbar references undefined variables
`UsersPage.vue:688` and `:691` were copy-pasted from the dictionary wrappers but the referenced symbols don't exist in this component:
```vue
<UButton ... @click="refreshToken++" />                <!-- refreshToken is undefined -->
<UDropdownMenu :items="crudContent?.columnMenuItems || []"> <!-- crudContent is undefined -->
```
There is no `refreshToken` ref and no `crudContent` template ref in `UsersPage` (verified). Consequences:
- **Refresh button does nothing** (and emits a Vue "property was accessed during render but is not defined" warning).
- **Column-visibility menu is permanently empty** — even though `UsersPage` *does* define a local `columnMenuItems` (`:549`). It should bind `:items="columnMenuItems"` and call `table.refresh()`.

### 4.2 🔴 Row selection is keyed by array index → corrupts on mutation
`UTable` is never given a `getRowId` (no `get-row-id` anywhere in `src`). Selection is therefore keyed by **row position**, and both pages read it back as:
```ts
// DictionaryCrudContent.vue:881, UsersPage.vue:446
Object.keys(rowSelection.value).filter(k => rowSelection.value[k])
  .map(k => table.data.value[Number(k)])
```
Because the data array is mutated by infinite-scroll append (`useServerTable.loadMore`), optimistic create (`unshift`) and optimistic delete (`filter`), the index→row mapping shifts under a live selection. After "load more" or a create, a checked checkbox can map to a *different* row, so bulk actions (delete / register / reject) can hit the wrong records. **Set `:get-row-id="(row) => row.id"`** and key selection by id.

### 4.3 🔴 Dynamic Tailwind width classes never apply
`CrudModulePage.vue:223` and `DictionaryCrudContent.vue:748`:
```ts
th: column.width ? `w-[${column.width}]` : undefined
```
Tailwind's JIT scanner cannot see interpolated class strings, so `w-[…]` is never generated — column widths silently don't work. (Compounding it, no entry in `crud-modules.ts` ever sets `width`, so the feature is also unused.) Use an inline `style="{ width }"` or a safelisted set of width tokens.

### 4.4 🟠 Dead status-badge branch in `uiColumns`
`DictionaryCrudContent.vue:721` renders a status `UBadge` inside the column `cell()`, but the same column is given `id: "status"` (`:457`, `getColumnId`) and the template also defines a `#status-cell` slot (`:1394`). With Nuxt UI's `UTable`, the named slot wins, so the `h(UBadge, …)` branch in `cell()` is **dead code**. Two implementations of the same rendering invite drift; keep one.

### 4.5 🟠 "Undo delete" recreates the entity via POST
`DictionaryCrudContent.vue:142–157` and `UsersPage.vue:55–69` implement undo by `apiCreateRequest(POST, body: {...item})`. This creates a *new* record (new id, server may reject the client-supplied `id`/relations), not a true restore. Also:
- Single-row delete gets the 8s undo toast, but **bulk `deleteSelected` does not** (`:1028`, `:455`) — inconsistent and irreversible. Prefer a soft-delete/restore endpoint or remove the undo illusion.

### 4.6 🟡 `CrudTableShell.findTbody()` falls back to a global query
`CrudTableShell.vue:37`:
```ts
return sectionRef.value?.querySelector("tbody") ?? document.querySelector("tbody");
```
The `document.querySelector("tbody")` fallback can observe an unrelated table (another table on the page, or one inside a modal), wiring the IntersectionObserver to the wrong element and firing spurious `loadMore`. Scope strictly to `sectionRef`.

### 4.7 🟡 `window.confirm` for destructive delete (dead path, but noted)
`CrudModulePage.vue:299` blocks the main thread with a native `confirm()` while the rest of the app uses `ConfirmDialog.vue`. Inconsistent UX; moot only because the component is unrouted.

### 4.8 🔵 Identical-branch ternary
`CrudModulePage.vue:349`: `config.title.startsWith('Цели') ? 'Создать' : \`Создать\`` — both arms produce `Создать`. Leftover/buggy.

---

## 5. Consistency & i18n

### 5.1 🟠 Hard-coded Russian strings across the whole table layer
`vue-i18n` is installed and actively used (`CrudDateRangeFilter`, dashboard, auth, error pages — 16 files). Yet every table string is a literal: `"Всего записей"` (`CrudDataTable:178`), `"Выбрать все строки"` (`:62`), all toasts, empty states, action labels, confirm copy, `"Да"/"Нет"` badges. None are localizable and they can't be reused/tested. Route table strings through `t()`.

### 5.2 🟠 Brittle status normalization
`DictionaryCrudContent.vue:426 normalizeStatusCode` infers status from substring matching that mixes English codes and Russian fragments (`"чернов"`, `"очеред"`, `"назнач"`, …). This is locale- and wording-fragile and drives delete-eligibility and workflow gating. Drive it off the backend `status.code` enum instead of label heuristics.

### 5.3 🟡 Two different filter UIs
`CrudModulePage` renders filters inline in a grid; `DictionaryCrudContent`/`UsersPage` use `CrudFilterModal`. Different interaction models for the same concept. Standardize on the modal (or a shared `<CrudFilters>` driven by `filterFields`).

### 5.4 🟡 Page-size selector with a single option
`pageSizeItems = [100]` (`CrudModulePage:114`; `CrudTableShell` defaults to `[100]`), and `resolvePageSize` (`useServerTable:114`) forces a minimum of 100. The `USelectMenu` for page size is therefore a no-op control. Either provide real options or drop the control.

---

## 6. Type safety

- 🟡 `CrudModulePage.vue:66` `type CrudRow = { id; [key: string]: any }` uses `any`; `DictionaryCrudContent` uses `unknown` for the same concept — pick one (prefer `unknown` + accessors).
- 🟡 Pervasive `JSON.parse(JSON.stringify(filters))` deep-clones (`CrudModulePage:118,232`, `DictionaryCrudContent:212,757`, `UsersPage:146,376`) — slow, drops `Date`/`undefined`, and ignores the existing `cloneFilters` helper in `useServerTable.ts:35`. Export and reuse one typed clone.
- 🟡 `getValueByPath` + `column.body?: (row: Record<string, any>) => …` (`types/table.ts:19`) loses row typing at the most important boundary.

---

## 7. Dead / no-op code

- 🟠 Entire `CrudModulePage.vue` (see §3.1).
- 🟡 `DictionariesPage.vue:82–84` — empty `watch(moduleKey, () => {})` no-op.
- 🟡 `DirectionsPage.vue` imports `SelectionActionBar` and defines `selectionActions`/`selectedCount` but **never renders the bar** in its template (Research/Samples/Tests do). Unused imports/state → lint noise and dead selection wiring.
- 🔵 Dead status-cell branch (§4.4) and identical ternary (§4.8).

---

## 8. Performance

- 🟡 `CrudTableShell.vue:73` observes the whole table subtree with `MutationObserver({ childList:true, subtree:true })` and re-queues `observeLastRow` on **every** DOM mutation (including per-cell skeleton swaps and each appended row). On large/fast-updating tables this thrashes. Debounce, or observe only `tbody` row count.
- 🟡 `useServerTable.ts:142,265,300` injects an artificial `minimumLoadingMs = 350ms` delay on **every** fetch and loadMore. Intentional anti-flicker, but it adds a guaranteed third-of-a-second to already-fast responses; consider only delaying when the response was *faster* than a flicker threshold and skipping entirely for `loadMore`.
- 🔵 `table-actions.ts:27` calls `resolveComponent` inside the cell render function (per row render) instead of once in factory scope.

---

## 9. Accessibility / UX polish

- 🔵 `CrudSearchControl.vue:19` autofocuses its input on mount; with a search box on every table page, navigation repeatedly steals focus and can scroll the viewport.
- 🔵 `RowContextMenu.vue` anchors the menu to a 1px hidden `aria-hidden` button — works, but keyboard users get no context-menu affordance.
- 🔵 Select-all / select-row `ariaLabel`s are hard-coded Russian (`CrudDataTable.vue:62,73`).
- 🔵 `SelectionActionBar.vue:40,54` uses `bg-[--ui-border]` (should be `bg-[var(--ui-border)]` / a token) — arbitrary-value class likely not emitted.

---

## 10. What's good (keep)

- `useServerTable` cleanly separates server concerns (cursor + offset, debounced global search, optimistic-friendly `data` ref, presets).
- Skeleton-row strategy (`table.ts` + `isSkeletonRow`) gives consistent loading UX and is reused everywhere.
- `CrudDataTable` slot-forwarding + `defineModel` for `columnVisibility`/`rowSelection` is a clean primitive — it's the right base to standardize on.
- `CrudDateRangeFilter` is the model citizen: i18n-driven, typed `defineModel`, presets extracted to `utils/date-range`.
- Per-entity table config (`crud-modules.ts`) is declarative and is the right direction — the refactor should push *more* behavior into this config and out of the god component.

---

## 11. Recommended refactor order

1. **Fix bugs first (low risk, high value):** §4.1 Users toolbar, §4.2 `getRowId`, §4.3 width classes, §4.4 dead status branch.
2. **Delete dead code:** remove `CrudModulePage.vue` body, move `CrudModuleConfig` → `shared/types/crud.ts`; remove §7 no-ops.
3. **Unify infrastructure:** one settings composable (§3.4), one clone helper (§6), one filter component (§5.3), i18n pass (§5.1).
4. **Decompose the god component (§3.3):** generic `<CrudTableHost>` + `workflow-commands.ts` registry + per-page composables; collapse the 4 wrappers (§3.5) into one.
5. **Harden:** status from backend codes (§5.2), real soft-delete (§4.5), observer scoping (§4.6/§8).

---

## Appendix — `bun run typecheck` evidence

`vue-tsc -p ./tsconfig.app.json` reports the following table-related errors (baseline is **RED**). These independently confirm the findings above:

```
src/modules/admin/pages/UsersPage.vue(549,7):  TS6133  'columnMenuItems' is declared but its value is never read.
src/modules/admin/pages/UsersPage.vue(688,92): TS2339  Property 'refreshToken' does not exist on type ...
src/modules/admin/pages/UsersPage.vue(691,36): TS2339  Property 'crudContent' does not exist on type ...
src/pages/DirectionsPage.vue(8,1):   TS6133  'SelectionActionBar' is declared but its value is never read.
src/pages/DirectionsPage.vue(27,7):  TS6133  'selectedCount' is declared but its value is never read.
src/pages/DirectionsPage.vue(29,7):  TS6133  'selectionActions' is declared but its value is never read.
```

- Lines 688/691 are the **broken Users toolbar** (§4.1): `refreshToken` and `crudContent` are undefined in that component, so the refresh button and column-visibility menu are non-functional.
- Line 549 proves the **local `columnMenuItems` is wired to nothing** — the template binds the (undefined) `crudContent?.columnMenuItems` instead.
- The three `DirectionsPage` errors confirm the **dead selection wiring** (§7) — `SelectionActionBar` is imported and `selectionActions`/`selectedCount` computed, but the bar is never rendered.

> Note: the earlier background run reported exit code 0 only because output was piped through `tail`; `vue-tsc` itself exits non-zero. CI should not mask the typecheck exit status.
