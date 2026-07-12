# Playwright demo recorder (`tests/e2e/demos`)

Standalone Playwright scripts that record **narrated screencasts** of the app —
a visible fake cursor, on-screen captions, deterministic waits — and render them
to `.mp4`. These are **not** `playwright test` specs; the runner ignores them
(no `*.spec.ts` name). They double as worked examples of driving this SPA.

## `record-entity-modals.mjs`

Walkthrough of the **direction** and **sample** detail modals with every tab:
`Карточка` → `Образцы`/`Исследования` → `Технический аудит`.

### Run

```bash
# Prereqs: backend :8080 seeded (scripts/seed_test_data.py) + frontend :5177 running.
#   make be-seed-data   &&   cd frontend && bun run dev

node tests/e2e/demos/record-entity-modals.mjs        # -> recordings/entity-modals.webm
./tests/e2e/demos/render.sh recordings/entity-modals.webm   # -> recordings/entity-modals.mp4
```

Outputs land in `frontend/recordings/` (gitignored). Use `DEMO_DEBUG=1` to also
get a per-beat timing log and a screenshot at each step — check timing before
rendering (if total ≫ the sum of the sleeps, a wait is hanging).

### Env overrides

| Var | Default | Notes |
|-----|---------|-------|
| `E2E_BASE_URL` | `http://localhost:5177` | frontend origin |
| `DEMO_USER` / `DEMO_PASS` | `admin` / `admin123` | seed user (bcrypt of `<username>123`) |
| `DEMO_LOCALE` | `ru` | `ru`\|`en`; must match the caption language |
| `RECORD_OUT_DIR` | `<frontend>/recordings` | where the `.webm` is written |
| `PLAYWRIGHT_CHROMIUM_PATH` | *(bundled)* | explicit chrome binary — same knob as `playwright.config.ts`; set it when the bundled Chromium build doesn't match this `@playwright/test` version |
| `DEMO_DEBUG` | — | `1` = timing log + per-beat screenshots |

## App-specific gotchas these scripts encode

Reusable knowledge for automating Biologic LIMS with Playwright:

- **Open a detail modal = right-click the row → `Просмотр`.** On the CRUD list
  tables a plain left-click only toggles the row's selection checkbox; double
  click does nothing. The modal opens from the row's context menu.
- **Locale is a localStorage key**, `biologic-lims-locale` (`ru`|`en`, see
  `src/shared/i18n/index.ts`). The app defaults to **English**, so tab labels are
  `Card`/`Samples` unless you seed `ru`. Set it in an `addInitScript` before the
  app boots; the recorder does this so captions and UI agree.
- **Auth survives a `storageState` snapshot** — it lives in cookies
  (`access_cookie`/`refresh_cookie`) + localStorage (`auth:user`, see
  `useAuth.ts`). Log in once in a throwaway context, reuse the state, and the
  video can start already-authenticated on the feature page.
- **Login selectors are locale-independent**: target `input[autocomplete=
  "username"]` / `input[autocomplete="current-password"]` and
  `button[type="submit"]` rather than the localized labels. (The e2e specs use
  `getByLabel('Username')` because they run in the default English locale — see
  `../support/auth.ts`.)
- **Tabs** are a Nuxt UI `UTabs`: `getByRole('tab', { name })`. The **Технический
  аудит** control is a separate icon button, not a tab —
  `getByTestId('entity-detail-technical-tab')`.
- **The modal is `:dismissible="false"`** (Esc/backdrop won't close it) and its
  header icon buttons have no accessible name — close it via the right-most small
  header button (the recorder locates it by geometry).
- **`page.goto()` does a hard reload**; the e2e specs prefer sidebar-click
  navigation (`../support/nav.ts`) to avoid slow blocked CDN refetches. The
  recorder uses `goto()` deliberately for clean section cuts.

## Related

- `../support/{auth,nav}.ts` — reusable login/navigation helpers for real specs.
- `playwright.video.config.ts` — records video for the actual `playwright test`
  suite (`bun run test:e2e:video`).
- Root skill `playwright-demo` / `flow-video-recorder` — the general recipe these
  scripts are built from.
