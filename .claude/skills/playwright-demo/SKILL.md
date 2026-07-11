---
name: playwright-demo
description: Record a polished screen-capture demo video of a web UI change with Playwright — injected fake cursor, on-screen captions, deterministic waits, and ffmpeg render (optional procedural music). Use when asked to "record/create a demo video", "screen-record this feature", "make a walkthrough/gif/mp4 of the UI", or to show a change working visually.
---

# Playwright Demo Recorder

Produce a clean, watchable demo video of a web feature: open the app on the
relevant page, drive the UI with a **visible fake cursor** and **top-center
captions**, and render an MP4. This skill encodes hard-won lessons so the first
take is usable instead of janky.

## When to use
- "Record a demo / walkthrough / screencast of <feature>"
- "Make an mp4/gif showing <UI change> working"
- A reviewer/MR needs a visual of a frontend change

## Prerequisites (check first)
- `node` available.
- Playwright + a Chromium build + ffmpeg. `npx playwright --version` works even
  if not in `node_modules`; Chromium/ffmpeg live under `~/Library/Caches/ms-playwright`
  (macOS) or `~/.cache/ms-playwright` (Linux). If missing: `npx playwright install chromium`.
- A running app and valid credentials (ask the user; never hardcode secrets in committed files — read from env).
- System `ffmpeg` for the webm→mp4 render (Playwright bundles its own ffmpeg only for capture).

## Workflow
1. **Decide the start page and choreography first.** For small features, START
   ON THE FEATURE PAGE — do NOT record the login. Pick 3-6 concrete actions that
   tell the story (load → action → *show result* → next).
2. Copy `assets/demo.template.js` into the project's gitignored scratch dir
   (e.g. `tmp/<feature>-demo/demo.js`). Never commit demo artifacts.
3. Fill in the config block (BASE url, start URL, login selectors/creds via env)
   and the `// ===== CHOREOGRAPHY =====` block with your steps + captions.
4. Run with `DEMO_DEBUG=1` first: `DEMO_DEBUG=1 node tmp/<feature>-demo/demo.js`.
   The debug run prints per-phase timing and saves screenshots so you can verify
   selectors, cursor, and captions WITHOUT re-watching the video.
5. Inspect the timing log. **If total ≫ sum of your sleeps, a wait is hanging**
   (see Gotcha 4). Fix before rendering.
6. Render the webm → mp4 with `assets/render.sh` (or the ffmpeg line below).
7. Verify by extracting a couple of frames (`ffmpeg -ss <t> -i out.mp4 -frames:v 1 f.png`)
   and Reading them — don't claim it looks right without checking pixels.
8. (Optional) Add procedural royalty-free music with `assets/make_funk.py` + mux.

## The reusable infrastructure (in the template)
- **Fake cursor**: Playwright does NOT render the OS cursor into the video, so we
  inject one via `context.addInitScript` — a deep-blue SVG arrow that follows
  `mousemove`, plus a click ripple on `mousedown`. Re-injected on every navigation.
- **Captions**: a fixed top-center banner; call `caption('text')` from the script.
  Default font is large (30px) and legible at video scale.
- **Glide helpers**: `glideTo(x,y)` / `glideToLocator(loc)` move the real mouse in
  steps (so the fake cursor animates) then click. Drive the mouse, not `.click()`,
  so motion is visible.
- **Login isolation**: log in inside a throwaway, NON-recorded context, snapshot
  `storageState`, then create the recorded context with that state and `goto` the
  feature page. The video starts on the page, not the login form.

## Gotchas (these WILL bite you — they're baked into the template)
1. **Start on the page, not login.** Use the storageState trick above.
2. **Inject the cursor** — the real one is invisible in recordings.
3. **Drive the mouse with `page.mouse.move(x,y,{steps})`** before clicking, or the
   cursor teleports and the video looks robotic.
4. **NEVER rely on Playwright's default 30s action timeout.** `boundingBox()`,
   `scrollIntoViewIfNeeded()`, `waitForSelector`, etc. wait up to 30s on a flaky/
   detached element — a couple of these silently add 60-80s of dead video. Always
   pass a short explicit `{ timeout: 2000-4000 }` and `.catch()` to fall back fast.
5. **Prefer deterministic state waits over fixed sleeps for correctness.** Wait for
   a DOM condition that proves the action landed (e.g. a result count changing),
   capped at a few seconds. `page.waitForResponse(predicate)` is great BUT if the
   predicate never matches it burns the FULL timeout — make the predicate loose
   (e.g. any POST to the API) or use a DOM-condition wait instead.
6. **Pause ON results.** Hold ~3s right after an operation's result renders so the
   viewer can read it; keep transitions snappy elsewhere. Dead time mid-video reads
   as "broken".
7. **GitLab `GlFilteredSearch` with `terms-as-tokens`**: free text is a *token* —
   type → `Enter` (commits the term) → `Enter` (submits/refetches). A single Enter
   does nothing visible. The **Clear (X) button clears the text but does NOT
   refetch** — press `Enter` after clicking it. Token filters: click the token
   suggestion, then the value suggestion, then `Enter`. Suggestions are
   `[data-testid="filtered-search-suggestion"]`; scope `getByText` to the search
   wrapper so it doesn't match a table column header of the same name.
8. **Render settings that play everywhere**: `-pix_fmt yuv420p -movflags +faststart`,
   `scale=<W>:-2`, constant `fps=30`. Playwright's webm is variable-framerate, so
   ffmpeg time-seeks on the raw webm are inaccurate — convert to CFR mp4 first, then
   sample frames.
9. **Muxing audio**: copy the video stream (`-c:v copy`) and only encode audio
   (`-c:a aac`), with `afade=t=out` near the end. Use `-shortest`.

## Render (webm → mp4)
```
ffmpeg -y -i page@*.webm -vf "scale=1440:-2,fps=30" -c:v libx264 -pix_fmt yuv420p -movflags +faststart out.mp4
```

## Optional music
`python3 assets/make_funk.py <out.wav> [seconds]` synthesizes a procedural,
fully royalty-free funk groove (no external assets). Mux:
```
ffmpeg -y -i out.mp4 -i out.wav -filter_complex "[1:a]afade=t=out:st=<dur-1.5>:d=1.5[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -shortest out-music.mp4
```

## Cleanup
Demo lives in a gitignored scratch dir. Keep `demo.js` (reusable) + the final mp4;
delete the raw `page@*.webm`, `dbg-*.png`, and any stray state dirs when done.
