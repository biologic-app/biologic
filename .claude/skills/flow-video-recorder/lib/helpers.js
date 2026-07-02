// Reusable helpers for narrated flow-video recordings via playwright-cli
// run-code. run-code does not support import/require, so copy this block
// into the top of every recording script rather than requiring it.
//
// Provides:
//   clickWithCursor(locator, opts?)  — moves the visible cursor to the
//     target, shows a click ripple, then clicks. Use for every click,
//     including nav-link clicks used for in-app navigation.
//   typeSlow(locator, text, delay?) — moves the cursor to the field, then
//     types character-by-character (default 60ms/key). Never use
//     locator.fill() for anything the video is meant to show.
//   toast(text, ms?) — small caption pill at the top of the viewport
//     (12px, dark background) explaining what's about to happen. Call
//     this *before* the action(s) it describes, then let it play out —
//     it already waits for its own duration.
//   dismissOnboarding(page) — dismisses this app's first-run product tour
//     (Escape) and cookie-consent toast ("Decline"), both dev-only widgets
//     that otherwise sit on screen for the rest of the recording. Call once
//     right after landing on /dashboard, before any other narration.
//
// See ../SKILL.md for the mandatory recording rules these enforce.

// Uses addInitScript (not a one-off evaluate) so the cursor survives every
// future page.goto()/reload — a plain evaluate()-injected element gets wiped
// by the very next hard navigation, which is exactly what happens if you
// install the cursor before navigating to the app's first page.
async function installCursor(page) {
  await page.addInitScript(() => {
    const mount = () => {
      if (document.getElementById('vr-cursor')) return;
      const style = document.createElement('style');
      style.textContent = `
        #vr-cursor { position: fixed; top: 20px; left: 20px; width: 22px; height: 22px;
          pointer-events: none; z-index: 2147483647;
          transition: left .45s cubic-bezier(.4,0,.2,1), top .45s cubic-bezier(.4,0,.2,1); }
        #vr-cursor svg { filter: drop-shadow(0 1px 3px rgba(0,0,0,.7)); }
        #vr-cursor.vr-click::after { content:''; position:absolute; left:-15px; top:-15px;
          width:38px; height:38px; border-radius:50%; border:3px solid rgba(59,130,246,.95);
          animation: vr-ripple .55s ease-out; }
        @keyframes vr-ripple { from{transform:scale(.25);opacity:1} to{transform:scale(1.5);opacity:0} }
      `;
      document.head.appendChild(style);
      const cursor = document.createElement('div');
      cursor.id = 'vr-cursor';
      cursor.innerHTML = '<svg width="22" height="22" viewBox="0 0 22 22">' +
        '<path d="M1 1 L1 18 L6 14 L9 20 L12 18.5 L9 12.5 L15 12.5 Z" ' +
        'fill="#fff" stroke="#111" stroke-width="1.2"/></svg>';
      document.body.appendChild(cursor);
    };
    if (document.body) mount();
    document.addEventListener('DOMContentLoaded', mount);
  });
}

async function moveCursorTo(page, locator) {
  await locator.scrollIntoViewIfNeeded();
  const box = await locator.boundingBox();
  if (!box) throw new Error('moveCursorTo: locator has no bounding box (not visible?)');
  const x = box.x + box.width / 2;
  const y = box.y + box.height / 2;
  await page.evaluate(([px, py]) => {
    const el = document.getElementById('vr-cursor');
    if (el) { el.style.left = px + 'px'; el.style.top = py + 'px'; }
  }, [x, y]);
  await page.mouse.move(x, y, { steps: 12 });
  await page.waitForTimeout(500);
}

async function pulseClick(page) {
  await page.evaluate(() => {
    const el = document.getElementById('vr-cursor');
    if (!el) return;
    el.classList.remove('vr-click');
    void el.offsetWidth; // restart the ripple animation
    el.classList.add('vr-click');
  });
  await page.waitForTimeout(300);
}

async function clickWithCursor(page, locator, opts) {
  await moveCursorTo(page, locator);
  await pulseClick(page);
  await locator.click(opts);
}

async function typeSlow(page, locator, text, delay = 60) {
  await moveCursorTo(page, locator);
  await pulseClick(page);
  await locator.pressSequentially(text, { delay });
  await page.waitForTimeout(300);
}

async function toast(page, text, ms = 1800) {
  await page.screencast.showOverlay(`
    <div style="position: fixed; top: 14px; left: 50%; transform: translateX(-50%);
      max-width: min(80vw, 640px); padding: 6px 14px; border-radius: 8px;
      background: rgba(15, 23, 42, 0.92); color: #fff;
      font: 500 12px/1.4 system-ui, -apple-system, sans-serif;
      text-align: center; z-index: 2147483647; pointer-events: none;
      box-shadow: 0 4px 14px rgba(0,0,0,.35);">
      ${text}
    </div>
  `, { duration: ms });
  await page.waitForTimeout(ms);
}

async function dismissOnboarding(page) {
  await page.waitForTimeout(300);
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: 'Decline' }).click({ timeout: 2000 }).catch(() => undefined);
}

// NOTE: this file is a copy-source, not something you pass to run-code
// directly. run-code --filename expects the file's content to be a single
// `async (page) => { ... }` expression (no import/require/module.exports) —
// paste these function declarations inside that body, above your
// flow-specific steps, in the actual recording script you write per video.
