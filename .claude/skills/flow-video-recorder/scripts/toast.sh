#!/usr/bin/env bash
# Shows a small narrative "toast" overlay at the top of the page during a
# playwright-cli video recording. Wraps playwright-cli run-code so callers
# don't have to hand-escape JS/HTML through the shell every time.
#
# Usage:
#   toast.sh "Текст на русском" [duration_ms] [session]
#
# duration_ms defaults to 1800. session is the playwright-cli -s= session
# name; omit for the default session.
set -euo pipefail

MESSAGE="${1:?usage: toast.sh <message> [duration_ms] [session]}"
DURATION="${2:-1800}"
SESSION="${3:-}"

TMP_JS="$(mktemp /tmp/pw-toast-XXXXXX.js)"
trap 'rm -f "$TMP_JS"' EXIT

# Written to a temp file (not passed inline) so the message text can contain
# quotes/backticks/Cyrillic without fighting shell quoting.
cat > "$TMP_JS" <<JS
async (page) => {
  await page.screencast.showOverlay(\`
    <div style="position: fixed; top: 14px; left: 50%; transform: translateX(-50%);
      max-width: min(80vw, 640px); padding: 6px 14px; border-radius: 8px;
      background: rgba(15, 23, 42, 0.92); color: #fff;
      font: 500 12px/1.4 system-ui, -apple-system, sans-serif;
      text-align: center; z-index: 2147483647; pointer-events: none;
      box-shadow: 0 4px 14px rgba(0,0,0,.35);">
      ${MESSAGE}
    </div>
  \`, { duration: ${DURATION} });
}
JS

if [ -n "$SESSION" ]; then
  playwright-cli -s="$SESSION" run-code --filename="$TMP_JS"
else
  playwright-cli run-code --filename="$TMP_JS"
fi
