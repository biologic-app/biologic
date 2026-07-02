---
name: flow-video-recorder
description: Record narrated demo videos of this app's user flows using playwright-cli, with a visible animated cursor, gradual (non-pasted) typing, and small top-of-screen narration toasts. Use whenever asked to "record a video", "снять видео", or "запиши демо" of a flow in this app.
allowed-tools: Bash(playwright-cli:*) Bash(npx:*)
---

# Flow video recorder

A house style on top of the base `playwright-cli` skill for recording
polished, narrated walkthroughs of this app's flows (e.g.
`docs/flows/*.flow.md`). Read `../playwright-cli/SKILL.md` first for raw
command syntax — this skill only adds recording-specific rules and helpers.

## Mandatory rules

These are not optional — a recording that violates any of them is not done:

1. **A visible cursor must show every click.** Never call `locator.click()`
   directly in a recording script. Always go through `clickWithCursor()` /
   `typeSlow()` from `lib/helpers.js` (§Helpers below), which move a custom
   on-page cursor icon to the target, show a click ripple, and only then
   perform the real action.
2. **Any navigation or page transition is a cursor click**, not a blind
   `page.goto()`. Use `page.goto()` only once, for the very first page load
   (e.g. the login page). Every subsequent transition — nav links, tabs,
   buttons, dropdown items, context-menu entries — must be a real click on
   a real element via `clickWithCursor()`, so the viewer sees what caused
   the transition.
3. **Any text entry is gradual, never pasted.** Never use `locator.fill()`
   or the base skill's `type` command in a recording (both either set the
   value instantly or type with 0ms delay — indistinguishable from a paste
   at video speed). Always use `typeSlow()`, which calls
   `locator.pressSequentially(text, { delay: 60 })` by default.
4. **Narration toast at the top, small text.** Explain what's about to
   happen with `toast()` before doing it — a small (12px) dark pill
   centered at the **top** of the viewport, not the bottom and not
   full-screen. Do not use `page.screencast.showChapter()` for this (it
   blurs and blocks the whole page) — that's a different, heavier tool for
   section breaks, not a running narration.

## Why one script, not one command per action

`playwright-cli <command>` is a separate OS process per invocation, and
connecting to the daemon takes several seconds. If you drive a recording
command-by-command (`video-start`, then a `click`, then a `type`, ...), that
multi-second connection overhead happens *while the video is recording* and
shows up as dead air between every action. Confirmed by timing a real run:
five simple actions produced a 55-second video.

The fix (also the pattern the base skill's video-recording reference
recommends for "hero scripts"): explore interactively with individual
commands to find the right locators, then write **one** script containing
the entire narrated flow and execute it with a single
`playwright-cli run-code --filename=script.js` call. All pacing inside that
script (`waitForTimeout`, the helpers' built-in delays) happens in-process,
with no per-action CLI overhead.

## Workflow

### 1. Explore (not recorded)

```bash
playwright-cli open http://localhost:5177/login
playwright-cli snapshot        # find refs / confirm labels and roles
playwright-cli click e12       # try things, iterate freely
```

Use this phase to nail down exact locators (`getByRole(...)`,
`getByLabel(...)`, `getByTestId(...)`) for every step of the flow you're
about to record. Nothing here needs to look good — it's throwaway.

### 2. Write one recording script

Start from `lib/helpers.js` — copy its function declarations into the top
of a new script file, then add the flow-specific steps below them, all
inside a single `async (page) => { ... }` body (run-code's required shape;
no import/require/module.exports). Skeleton:

```js
async (page) => {
  // --- paste lib/helpers.js contents here (installCursor, moveCursorTo,
  //     pulseClick, clickWithCursor, typeSlow, toast) ---

  await page.screencast.start({ path: 'recordings/my-flow.webm', size: { width: 1280, height: 800 } });
  await installCursor(page);
  // This app has a dev-only annotation widget that occasionally intercepts
  // pointer events and hangs a click for the full timeout — block it before
  // navigating anywhere. (Same root cause as the Playwright Test e2e suite.)
  await page.route('**/feedback/annotator.min.js', (route) => route.abort());

  await page.goto('http://localhost:5177/login');
  await toast(page, 'Входим в систему под нужной учётной записью');
  await typeSlow(page, page.getByLabel('Username'), 'someuser');
  await typeSlow(page, page.getByLabel('Password'), 'somepass');
  await clickWithCursor(page, page.getByRole('button', { name: 'Sign in' }));
  await page.waitForURL('**/dashboard');
  await dismissOnboarding(page); // first-run tour + cookie toast, dev-only widgets
  await page.waitForTimeout(1200);

  // ...rest of the flow, one toast() before each logical step, one
  // clickWithCursor()/typeSlow() per interaction...

  await page.screencast.stop();
}
```

Notes:
- `page.screencast.start/stop` (inside the script) is equivalent to the CLI's
  `video-start`/`video-stop` but keeps everything in the one process — prefer
  it over the CLI commands for recordings.
- Do **not** enable `video-show-actions` for scripted recordings — it only
  annotates CLI/MCP-level commands, not raw `page.*` calls made from inside
  `run-code`, so it has no effect here. The custom cursor from
  `lib/helpers.js` is what makes clicks visible in this workflow.
- Save recordings under `recordings/` (gitignored) unless the user asks for
  the file to be committed/attached somewhere.

### 3. Run it

```bash
playwright-cli run-code --filename=recordings/my-flow.js
```

One CLI invocation for the whole video. Expect it to take roughly as long
as the recording itself (plus one connection overhead at the start), not
minutes longer.

### 4. Sanity-check before showing it

Screenshots do **not** show `page.screencast.showOverlay()` content (it only
composites into the video stream), so you cannot verify toasts/cursor via
`playwright-cli screenshot`. Extract a frame from the actual output instead:

```bash
/opt/pw-browsers/ffmpeg-1011/ffmpeg-linux -y -ss 3.5 -i recordings/my-flow.webm \
  -frames:v 1 -update 1 /tmp/check.png
```

Pick a few timestamps you know correspond to a toast or a click (from the
script's own `waitForTimeout` accounting) and read the resulting PNG.

## Helpers reference

`lib/helpers.js` — copy-source for `installCursor`, `moveCursorTo`,
`pulseClick`, `clickWithCursor(page, locator, opts?)`,
`typeSlow(page, locator, text, delay?)`, `toast(page, text, ms?)`.

## Quick one-off toasts (exploration/debugging only)

For quick manual checks during the exploration phase (not for the final
recording — see the one-script rule above), two standalone wrappers exist:

```bash
scripts/toast.sh "Текст на русском" [duration_ms] [session]
scripts/type-slow.sh "getByLabel('Username')" "text" [delay_ms] [session]
```

Both just wrap a single `playwright-cli run-code` call each, so each one
still costs a full daemon round-trip — fine for a one-off check, wrong tool
for a multi-step video.
