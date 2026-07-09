/* eslint-disable */
// Playwright demo recorder — fake cursor + captions + deterministic waits.
// Copy into a gitignored scratch dir, edit the CONFIG and CHOREOGRAPHY blocks.
//
//   DEMO_DEBUG=1 node demo.js     # timing log + screenshots while iterating
//   node demo.js                  # quiet run -> page@*.webm in this dir
//
// Then render:  ffmpeg -y -i page@*.webm -vf "scale=1440:-2,fps=30" \
//                 -c:v libx264 -pix_fmt yuv420p -movflags +faststart out.mp4

// --- resolve playwright wherever it lives (node_modules, npx cache, or PW_PATH) ---
function loadChromium() {
  const tries = [];
  if (process.env.PW_PATH) tries.push(process.env.PW_PATH);
  tries.push('playwright', 'playwright-core');
  for (const t of tries) { try { return require(t).chromium; } catch (e) {} }
  const fs = require('fs'), path = require('path'), os = require('os');
  const npx = path.join(os.homedir(), '.npm', '_npx');
  try {
    for (const d of fs.readdirSync(npx)) {
      const p = path.join(npx, d, 'node_modules', 'playwright');
      if (fs.existsSync(p)) return require(p).chromium;
    }
  } catch (e) {}
  throw new Error('playwright not found — set PW_PATH or `npx playwright install chromium`');
}
const chromium = loadChromium();

// ===== CONFIG (edit me) =====
const BASE = process.env.APP_URL || 'http://gdk.test:3000';
const START_URL = process.env.START_URL || `${BASE}/`;     // the FEATURE page (not login)
const READY_SELECTOR = process.env.READY_SELECTOR || 'body'; // wait for this before acting
const OUT_DIR = __dirname;
const DEBUG = process.env.DEMO_DEBUG === '1';
const VIEWPORT = { width: 1440, height: 900 };
const RESULT_PAUSE = 3000; // hold on a result so the viewer can read it
const BEAT = 650;          // small beat between minor actions
// Login (optional): done in a NON-recorded context so the video starts on the page.
const LOGIN = {
  enabled: process.env.LOGIN !== '0',
  url: `${BASE}/users/sign_in`,
  user: process.env.APP_USER || 'root',
  pass: process.env.APP_PASS || '',
  userSel: '#user_login',
  passSel: '#user_password',
  submitSel: '[data-testid="sign-in-button"], button[type="submit"]',
};
// ============================

// --- injected deep-blue pointer cursor + click ripple + caption banner ---
const initScript = () => {
  const CUR = '__demo_cursor__', CAP = '__demo_caption__', BLUE = '#0b2a6b';
  function ensure() {
    if (!document.body) return;
    if (!document.getElementById(CUR)) {
      const c = document.createElement('div');
      c.id = CUR;
      Object.assign(c.style, {
        position: 'fixed', top: '0', left: '0', width: '26px', height: '26px',
        zIndex: '2147483647', pointerEvents: 'none',
        filter: 'drop-shadow(0 1px 2px rgba(0,0,0,.45))', transform: 'translate(-2px,-2px)',
      });
      c.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">' +
        '<path d="M3 2 L3 20.5 L8 15.6 L11.4 22.6 L14.6 21.1 L11.1 14.2 L18 14.2 Z" ' +
        'fill="' + BLUE + '" stroke="#fff" stroke-width="1.3" stroke-linejoin="round"/></svg>';
      document.body.appendChild(c);
    }
    if (!document.getElementById(CAP)) {
      const b = document.createElement('div');
      b.id = CAP;
      Object.assign(b.style, {
        position: 'fixed', top: '14px', left: '50%', transform: 'translateX(-50%)',
        maxWidth: '90%', padding: '18px 32px', borderRadius: '10px',
        background: 'rgba(11,26,64,0.92)', color: '#fff',
        font: '600 30px/1.3 -apple-system, system-ui, sans-serif',
        zIndex: '2147483647', pointerEvents: 'none', opacity: '0',
        transition: 'opacity .25s ease', boxShadow: '0 4px 14px rgba(0,0,0,.35)', letterSpacing: '.2px',
      });
      document.body.appendChild(b);
    }
  }
  const move = (x, y) => { ensure(); const c = document.getElementById(CUR); if (c) { c.style.left = x + 'px'; c.style.top = y + 'px'; } };
  const ripple = (x, y) => {
    if (!document.body) return;
    const r = document.createElement('div');
    Object.assign(r.style, {
      position: 'fixed', left: x + 'px', top: y + 'px', width: '12px', height: '12px',
      marginLeft: '-6px', marginTop: '-6px', borderRadius: '50%',
      border: '2px solid rgba(11,42,107,0.85)', background: 'rgba(28,72,168,0.30)',
      zIndex: '2147483646', pointerEvents: 'none', transform: 'scale(0.3)', opacity: '0.85',
      transition: 'transform .45s ease-out, opacity .45s ease-out',
    });
    document.body.appendChild(r);
    requestAnimationFrame(() => { r.style.transform = 'scale(3.2)'; r.style.opacity = '0'; });
    setTimeout(() => r.remove(), 520);
  };
  document.addEventListener('mousemove', (e) => move(e.clientX, e.clientY), true);
  document.addEventListener('mousedown', (e) => ripple(e.clientX, e.clientY), true);
  window.addEventListener('DOMContentLoaded', ensure);
  window.__demoCaption = (t) => { ensure(); const b = document.getElementById(CAP); if (b) { b.textContent = t; b.style.opacity = t ? '1' : '0'; } };
  ensure();
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  const browser = await chromium.launch({ headless: true });

  let storageState;
  if (LOGIN.enabled) {
    const lc = await browser.newContext({ viewport: VIEWPORT, ignoreHTTPSErrors: true });
    const lp = await lc.newPage();
    await lp.goto(LOGIN.url, { waitUntil: 'domcontentloaded' });
    await lp.fill(LOGIN.userSel, LOGIN.user);
    await lp.fill(LOGIN.passSel, LOGIN.pass);
    await lp.click(LOGIN.submitSel);
    await lp.waitForLoadState('networkidle').catch(() => {});
    storageState = await lc.storageState();
    await lc.close();
  }

  const context = await browser.newContext({
    viewport: VIEWPORT,
    recordVideo: { dir: OUT_DIR, size: VIEWPORT },
    ignoreHTTPSErrors: true,
    storageState,
  });
  await context.addInitScript(initScript);
  const page = await context.newPage();
  await page.mouse.move(VIEWPORT.width / 2, VIEWPORT.height / 2);

  let shot = 0;
  const T0 = Date.now();
  const mark = (m) => { if (DEBUG) console.log(`[${((Date.now() - T0) / 1000).toFixed(1)}s] ${m}`); };
  const caption = (t) => page.evaluate((x) => window.__demoCaption && window.__demoCaption(x), t).catch(() => {});
  const debugShot = async (name) => { if (DEBUG) await page.screenshot({ path: `${OUT_DIR}/dbg-${String(++shot).padStart(2, '0')}-${name}.png` }).catch(() => {}); };

  // --- helpers: ALWAYS use short explicit timeouts (default is 30s and will hang) ---
  async function glideTo(x, y, steps = 28) { await page.mouse.move(x, y, { steps }); await sleep(160); }
  async function glideToLocator(loc, { click = true } = {}) {
    await loc.scrollIntoViewIfNeeded({ timeout: 2500 }).catch(() => {});
    const box = await loc.boundingBox({ timeout: 2500 }).catch(() => null);
    if (!box) throw new Error('no bounding box');
    await glideTo(box.x + box.width / 2, box.y + box.height / 2);
    if (click) { await page.mouse.down(); await sleep(80); await page.mouse.up(); await sleep(180); }
    return box;
  }
  async function clickText(text, opts = {}) { await glideToLocator(page.getByText(text, { exact: opts.exact || false }).first()); }
  async function typeInto(loc, text, delay = 90) { await glideToLocator(loc); await page.keyboard.type(text, { delay }); }
  // Wait (capped) for a page-evaluated condition to become true — deterministic, fast.
  async function waitUntil(fn, arg, cap = 4000) {
    await page.waitForFunction(fn, arg, { timeout: cap }).catch(() => {});
    await sleep(200);
  }

  try {
    mark('goto start');
    await page.goto(START_URL, { waitUntil: 'domcontentloaded' });
    await page.locator(READY_SELECTOR).first().waitFor({ timeout: 30000 });
    mark('ready');

    // ===== CHOREOGRAPHY (edit me) =====
    // Tell the story in 3-6 beats. caption() narrates; glide* drives the cursor.
    // Pause RESULT_PAUSE right after a result renders; keep transitions to BEAT.
    await caption('Here is the feature');
    await debugShot('start');
    await sleep(1800);

    // Example — type into a search box and show results:
    //   const search = page.getByTestId('my-search-input');
    //   await caption('Search by name');
    //   await typeInto(search, 'issue');
    //   await page.keyboard.press('Enter');
    //   await waitUntil(() => document.querySelectorAll('[data-testid="row"]').length < 20, null);
    //   await caption('Filtered results'); await sleep(RESULT_PAUSE);

    // Example — click a button:
    //   await caption('Open the panel');
    //   await glideToLocator(page.getByRole('button', { name: 'Open' }));
    //   await sleep(BEAT);

    // GitLab GlFilteredSearch (terms-as-tokens) free text: type -> Enter (commit) -> Enter (submit)
    // Token: click suggestion 'X' then value, then Enter. Clear (X) button needs a following Enter to refetch.

    await caption('Done ✓');
    await sleep(2200);
    await caption('');
    // ==================================

    console.log('DEMO_OK');
  } catch (err) {
    console.error('DEMO_ERROR', err && err.message);
    await page.screenshot({ path: `${OUT_DIR}/error.png`, fullPage: true }).catch(() => {});
  } finally {
    const video = page.video();
    await context.close(); // finalizes the video
    if (video) { const p = await video.path().catch(() => null); if (p) console.log('VIDEO_PATH', p); }
    await browser.close();
  }
}

main();
