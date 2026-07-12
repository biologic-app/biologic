/* eslint-disable */
/**
 * Playwright screencast example — Biologic LIMS entity detail modals.
 *
 * Records a narrated walkthrough of the direction & sample detail modals with
 * every tab (Карточка, Образцы/Исследования, Технический аудит). It is a
 * standalone Node script (NOT a `playwright test` spec) that injects a visible
 * fake cursor + on-screen captions and captures a `.webm`, which you then
 * render to `.mp4` with `./render.sh`.
 *
 * It doubles as a reference for automating THIS app — see the app-specific
 * notes in README.md and inline below.
 *
 *   # 1. backend :8080 seeded + frontend :5177 must be running
 *   # 2. record (writes recordings/<name>.webm):
 *   node tests/e2e/demos/record-entity-modals.mjs
 *   # 3. render to mp4:
 *   ./tests/e2e/demos/render.sh recordings/entity-modals.webm
 *
 * Env overrides:
 *   E2E_BASE_URL              frontend origin           (default http://localhost:5177)
 *   DEMO_USER / DEMO_PASS     login credentials         (default admin / admin123, seed user)
 *   DEMO_LOCALE               ru | en                   (default ru — matches the captions)
 *   RECORD_OUT_DIR            output directory          (default <frontend>/recordings)
 *   PLAYWRIGHT_CHROMIUM_PATH  explicit chrome binary    (same knob as playwright.config.ts;
 *                             leave unset to use Playwright's bundled browser)
 *   DEMO_DEBUG=1              per-phase timing log + a screenshot at each beat
 */
import { chromium } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// ===== CONFIG =====
const BASE = process.env.E2E_BASE_URL || 'http://localhost:5177'
const USER = process.env.DEMO_USER || 'admin'
const PASS = process.env.DEMO_PASS || 'admin123'
const LOCALE = process.env.DEMO_LOCALE || 'ru'
// Bundled Chromium may not match this @playwright/test version on some images;
// point at a pre-installed browser explicitly, exactly like playwright.config.ts.
const EXEC = process.env.PLAYWRIGHT_CHROMIUM_PATH || undefined
const OUT_DIR = process.env.RECORD_OUT_DIR || path.resolve(__dirname, '../../../recordings')
const DEBUG = process.env.DEMO_DEBUG === '1'
const VIEWPORT = { width: 1440, height: 900 }
const RESULT_PAUSE = 3000 // hold on a rendered result so a viewer can read it
const BEAT = 650          // small beat between minor actions
// i18n locale key (src/shared/i18n/index.ts) — seeded into localStorage so the
// whole UI (and therefore the tab labels below) renders in DEMO_LOCALE.
const LOCALE_STORAGE_KEY = 'biologic-lims-locale'
// ==================

// Injected once per navigation: a deep-blue pointer that follows the real mouse
// (Playwright never renders the OS cursor into the video), a click ripple, and a
// fixed top-center caption banner driven by window.__demoCaption(text).
const initCursorAndCaptions = () => {
  const CUR = '__demo_cursor__', CAP = '__demo_caption__', BLUE = '#0b2a6b'
  function ensure() {
    if (!document.body) return
    if (!document.getElementById(CUR)) {
      const c = document.createElement('div')
      c.id = CUR
      Object.assign(c.style, {
        position: 'fixed', top: '0', left: '0', width: '26px', height: '26px',
        zIndex: '2147483647', pointerEvents: 'none',
        filter: 'drop-shadow(0 1px 2px rgba(0,0,0,.45))', transform: 'translate(-2px,-2px)',
      })
      c.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">' +
        '<path d="M3 2 L3 20.5 L8 15.6 L11.4 22.6 L14.6 21.1 L11.1 14.2 L18 14.2 Z" ' +
        'fill="' + BLUE + '" stroke="#fff" stroke-width="1.3" stroke-linejoin="round"/></svg>'
      document.body.appendChild(c)
    }
    if (!document.getElementById(CAP)) {
      const b = document.createElement('div')
      b.id = CAP
      Object.assign(b.style, {
        position: 'fixed', top: '14px', left: '50%', transform: 'translateX(-50%)',
        maxWidth: '90%', padding: '16px 30px', borderRadius: '10px',
        background: 'rgba(11,26,64,0.92)', color: '#fff',
        font: '600 28px/1.3 -apple-system, system-ui, sans-serif',
        zIndex: '2147483647', pointerEvents: 'none', opacity: '0',
        transition: 'opacity .25s ease', boxShadow: '0 4px 14px rgba(0,0,0,.35)', letterSpacing: '.2px',
      })
      document.body.appendChild(b)
    }
  }
  const move = (x, y) => { ensure(); const c = document.getElementById(CUR); if (c) { c.style.left = x + 'px'; c.style.top = y + 'px' } }
  const ripple = (x, y) => {
    if (!document.body) return
    const r = document.createElement('div')
    Object.assign(r.style, {
      position: 'fixed', left: x + 'px', top: y + 'px', width: '12px', height: '12px',
      marginLeft: '-6px', marginTop: '-6px', borderRadius: '50%',
      border: '2px solid rgba(11,42,107,0.85)', background: 'rgba(28,72,168,0.30)',
      zIndex: '2147483646', pointerEvents: 'none', transform: 'scale(0.3)', opacity: '0.85',
      transition: 'transform .45s ease-out, opacity .45s ease-out',
    })
    document.body.appendChild(r)
    requestAnimationFrame(() => { r.style.transform = 'scale(3.2)'; r.style.opacity = '0' })
    setTimeout(() => r.remove(), 520)
  }
  document.addEventListener('mousemove', (e) => move(e.clientX, e.clientY), true)
  document.addEventListener('mousedown', (e) => ripple(e.clientX, e.clientY), true)
  window.addEventListener('DOMContentLoaded', ensure)
  window.__demoCaption = (t) => { ensure(); const b = document.getElementById(CAP); if (b) { b.textContent = t; b.style.opacity = t ? '1' : '0' } }
  ensure()
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true })
  const browser = await chromium.launch({ headless: true, executablePath: EXEC, args: ['--no-sandbox'] })

  // --- Log in inside a throwaway, NON-recorded context, then snapshot storage.
  // Auth persists in cookies (access/refresh) + localStorage (auth:user, see
  // useAuth.ts), so a storageState snapshot lets the recorded video start
  // already-authenticated on the feature page instead of on the login form.
  // Selectors are locale-independent (autocomplete attrs), so login works in ru or en.
  const lc = await browser.newContext({ viewport: VIEWPORT, ignoreHTTPSErrors: true })
  const lp = await lc.newPage()
  await lp.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded' })
  await lp.locator('input[autocomplete="username"]').fill(USER)
  await lp.locator('input[autocomplete="current-password"]').fill(PASS)
  await lp.locator('button[type="submit"]').click()
  await lp.waitForURL('**/dashboard', { timeout: 15000 }).catch(() => {})
  await sleep(800)
  const storageState = await lc.storageState()
  await lc.close()

  // --- Recorded context: force the locale, inject cursor + captions.
  const context = await browser.newContext({
    viewport: VIEWPORT,
    recordVideo: { dir: OUT_DIR, size: VIEWPORT },
    ignoreHTTPSErrors: true,
    storageState,
  })
  await context.addInitScript(([key, loc]) => { try { localStorage.setItem(key, loc) } catch { } }, [LOCALE_STORAGE_KEY, LOCALE])
  await context.addInitScript(initCursorAndCaptions)
  const page = await context.newPage()
  await page.mouse.move(VIEWPORT.width / 2, VIEWPORT.height / 2)

  let shot = 0
  const T0 = Date.now()
  const mark = (m) => { if (DEBUG) console.log(`[${((Date.now() - T0) / 1000).toFixed(1)}s] ${m}`) }
  const caption = (t) => page.evaluate((x) => window.__demoCaption && window.__demoCaption(x), t).catch(() => { })
  const debugShot = async (name) => { if (DEBUG) await page.screenshot({ path: path.join(OUT_DIR, `dbg-${String(++shot).padStart(2, '0')}-${name}.png`) }).catch(() => { }) }

  // Drive the REAL mouse in steps so the injected cursor animates (never .click()).
  // ALWAYS pass short explicit timeouts — Playwright's 30s default silently turns
  // one flaky element into ~30s of dead video.
  async function glideTo(x, y, steps = 26) { await page.mouse.move(x, y, { steps }); await sleep(150) }
  async function glideToLocator(loc) {
    await loc.scrollIntoViewIfNeeded({ timeout: 2500 }).catch(() => { })
    const box = await loc.boundingBox({ timeout: 3000 }).catch(() => null)
    if (!box) throw new Error('no bounding box for locator')
    await glideTo(box.x + box.width / 2, box.y + box.height / 2)
    await page.mouse.down(); await sleep(80); await page.mouse.up(); await sleep(200)
    return box
  }
  // Deterministic, capped wait for a DOM condition — proves the action landed.
  async function waitUntil(fn, cap = 5000) { await page.waitForFunction(fn, null, { timeout: cap }).catch(() => { }); await sleep(200) }

  // APP-SPECIFIC: on the CRUD list tables a left-click only toggles the row's
  // selection checkbox — the detail modal opens from the row's RIGHT-CLICK
  // context menu ("Просмотр"). (Left/double click do NOT open it.)
  async function openRowModal(index = 0) {
    const row = page.locator('tbody tr').nth(index)
    const box = await row.boundingBox({ timeout: 4000 })
    const px = box.x + 300, py = box.y + box.height / 2
    await glideTo(px, py)
    await page.mouse.click(px, py, { button: 'right' })
    await sleep(500)
    const view = page.getByRole('menuitem', { name: /Просмотр/ }).first()
    await view.waitFor({ timeout: 3000 })
    await glideToLocator(view)
    await waitUntil(() => !!document.querySelector('[role="dialog"] [role="tab"]'))
  }

  // Literal Russian status labels (status-timeline.ts DIRECTION_STATUS_FLOW /
  // SAMPLE_STATUS_FLOW + the rejected branch) — used to find two list rows
  // with visibly DIFFERENT statuses without assuming seed-data row order.
  const DIRECTION_STATUS_LABELS = ['Черновик', 'Зарегистрировано', 'В работе', 'Частично выполнено', 'Выполнено']
  const SAMPLE_STATUS_LABELS = ['На регистрации', 'Зарегистрирован', 'На исследовании', 'Обработан', 'Закрыт', 'Брак']

  async function rowStatusLabels(labels) {
    return page.evaluate((ls) => {
      return [...document.querySelectorAll('tbody tr')].map((r) => {
        const text = r.innerText || ''
        return ls.find((l) => text.includes(l)) || null
      })
    }, labels)
  }

  // Returns { index, label } for the first row (beyond `afterIndex`) whose
  // status label differs from `excludeLabel`, or null if the whole (scanned)
  // list shares one status.
  async function findDifferentStatusRow(labels, excludeLabel, afterIndex = 0, maxScan = 25) {
    const statuses = await rowStatusLabels(labels)
    for (let i = afterIndex; i < Math.min(statuses.length, maxScan); i++) {
      if (statuses[i] && statuses[i] !== excludeLabel) return { index: i, label: statuses[i] }
    }
    return null
  }

  // The modal is `:dismissible="false"` (Esc/backdrop do nothing) and its header
  // icon buttons carry no accessible name — close via the right-most small button.
  async function closeModal() {
    const c = await page.evaluate(() => {
      const d = document.querySelector('[role="dialog"]') || document.body
      const r = [...d.querySelectorAll('button')]
        .map((b) => b.getBoundingClientRect())
        .filter((box) => box.y < 110 && box.width < 60)
        .sort((a, z) => z.x - a.x)[0]
      return r ? { x: r.x + r.width / 2, y: r.y + r.height / 2 } : null
    })
    if (c) { await glideTo(c.x, c.y); await page.mouse.down(); await sleep(80); await page.mouse.up(); await sleep(300) }
    await waitUntil(() => !document.querySelector('[role="dialog"]'), 3000)
  }

  // Tabs are a Nuxt UI UTabs (role="tab", accessible name = label); the technical
  // audit is a separate icon button with a data-testid, not a tab.
  const openTab = (name) => glideToLocator(page.getByRole('tab', { name }))
  const openTech = () => glideToLocator(page.getByTestId('entity-detail-technical-tab'))

  // The direction's "Образцы" tab is a sample->research tree (EntityRelatedTab.vue):
  // each sample row has an expand toggle, aria-label "Развернуть исследования"
  // (collapsed) / "Свернуть исследования" (expanded). Expand up to `count` of them
  // so nested research rows become visible in the recording.
  async function expandTreeRows(count = 2) {
    const toggles = page.getByRole('button', { name: 'Развернуть исследования' })
    const n = Math.min(count, await toggles.count().catch(() => 0))
    for (let i = 0; i < n; i++) {
      const t = toggles.nth(0) // re-query each time: expanding shifts remaining rows down, not the toggle list length
      await glideToLocator(t).catch(() => { })
      await sleep(300)
    }
  }

  try {
    // ========= DIRECTIONS (/directions) =========
    mark('goto directions')
    await page.goto(`${BASE}/directions`, { waitUntil: 'domcontentloaded' })
    await page.locator('tbody tr').first().waitFor({ timeout: 30000 })
    await sleep(600)
    await caption('Раздел «Направления»'); await debugShot('dir-list'); await sleep(2200)

    const dirStatuses = await rowStatusLabels(DIRECTION_STATUS_LABELS)
    const dirFirstLabel = dirStatuses[0] || '?'
    await caption(`Открываем направление — статус «${dirFirstLabel}»`); await sleep(BEAT)
    await openRowModal(0); mark('dir modal open'); await debugShot('dir-open')

    await caption('Карточка — данные и жизненный цикл'); await sleep(RESULT_PAUSE); await debugShot('dir-card')

    await caption('Вкладка «Образцы» направления'); await openTab('Образцы'); await sleep(500)
    await debugShot('dir-related'); await sleep(1400)

    await caption('Разворачиваем образец — видно его исследования'); await sleep(400)
    await expandTreeRows(2); mark('dir tree expanded')
    await debugShot('dir-related-expanded'); await sleep(RESULT_PAUSE)

    await caption('Технический аудит — история изменений'); await openTech(); await sleep(400)
    await debugShot('dir-tech'); await sleep(RESULT_PAUSE)

    await caption('Готово ✓'); await closeModal(); await sleep(800)

    // Second direction, a DIFFERENT status, to show the lifecycle/badges vary.
    const otherDir = await findDifferentStatusRow(DIRECTION_STATUS_LABELS, dirFirstLabel)
    if (otherDir) {
      await caption(`Направление со статусом «${otherDir.label}»`); await sleep(BEAT)
      await openRowModal(otherDir.index); mark('dir modal open (2nd status)'); await debugShot('dir-open-2')
      await caption(`Карточка — статус «${otherDir.label}»`); await sleep(RESULT_PAUSE); await debugShot('dir-card-2')
      await caption('Готово ✓'); await closeModal(); await sleep(800)
    }
    await caption(''); await sleep(400)

    // ========= SAMPLES (/samples) =========
    await caption('Теперь — раздел «Образцы»'); await sleep(BEAT)
    await page.goto(`${BASE}/samples`, { waitUntil: 'domcontentloaded' })
    await page.locator('tbody tr').first().waitFor({ timeout: 30000 })
    await sleep(600)
    await caption('Раздел «Образцы»'); await debugShot('sample-list'); await sleep(2000)

    const sampleStatuses = await rowStatusLabels(SAMPLE_STATUS_LABELS)
    const sampleFirstLabel = sampleStatuses[0] || '?'
    await caption(`Открываем образец — статус «${sampleFirstLabel}»`); await sleep(BEAT)
    await openRowModal(0); mark('sample modal open'); await debugShot('sample-open')

    await caption('Карточка образца'); await sleep(RESULT_PAUSE); await debugShot('sample-card')

    await caption('Вкладка «Исследования»'); await openTab('Исследования'); await sleep(400)
    await debugShot('sample-related'); await sleep(RESULT_PAUSE)

    // Drill into a research goal from the sample's flat "Исследования" list —
    // opens a NESTED modal on the same detailStack (pushDetail), same
    // ":dismissible=false" modal, same "Открыть карточку" aria-label as the
    // tree table's leaf rows (EntityRelatedTab.vue).
    await caption('Открываем цель исследования'); await sleep(BEAT)
    await glideToLocator(page.getByRole('button', { name: 'Открыть карточку' }).first())
    await waitUntil(() => !!document.querySelector('[role="dialog"] [role="tab"]'))
    mark('research modal open'); await debugShot('research-open')

    await caption('Карточка исследования'); await sleep(RESULT_PAUSE); await debugShot('research-card')

    await caption('Вкладка «Тесты» — результаты и вердикт врача'); await openTab('Тесты'); await sleep(400)
    await debugShot('research-tests'); await sleep(RESULT_PAUSE)

    await caption('Технический аудит исследования'); await openTech(); await sleep(400)
    await debugShot('research-tech'); await sleep(RESULT_PAUSE)

    // popDetail(): closes ONE stack level (research -> back to the sample),
    // NOT the whole modal — the sample modal is still open underneath.
    await caption('Назад — к карточке образца'); await closeModal(); await sleep(600)

    await caption('Технический аудит образца'); await openTech(); await sleep(400)
    await debugShot('sample-tech'); await sleep(RESULT_PAUSE)

    await caption('Готово ✓'); await closeModal(); await sleep(800)

    // Second sample, a DIFFERENT status.
    const otherSample = await findDifferentStatusRow(SAMPLE_STATUS_LABELS, sampleFirstLabel)
    if (otherSample) {
      await caption(`Образец со статусом «${otherSample.label}»`); await sleep(BEAT)
      await openRowModal(otherSample.index); mark('sample modal open (2nd status)'); await debugShot('sample-open-2')
      await caption(`Карточка — статус «${otherSample.label}»`); await sleep(RESULT_PAUSE); await debugShot('sample-card-2')
      await caption('Готово ✓'); await closeModal(); await sleep(800)
    }
    await caption(''); await sleep(600)

    console.log('DEMO_OK')
  } catch (err) {
    console.error('DEMO_ERROR', err && err.message)
    await page.screenshot({ path: path.join(OUT_DIR, 'error.png'), fullPage: true }).catch(() => { })
    process.exitCode = 1
  } finally {
    const video = page.video()
    await context.close() // finalizes the video file
    if (video) {
      const src = await video.path().catch(() => null)
      if (src) {
        const dest = path.join(OUT_DIR, 'entity-modals.webm')
        try { fs.renameSync(src, dest); console.log('VIDEO', dest) }
        catch { console.log('VIDEO', src) }
      }
    }
    await browser.close()
  }
}

main()
