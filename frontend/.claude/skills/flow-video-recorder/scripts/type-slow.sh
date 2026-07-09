#!/usr/bin/env bash
# Types text into a field character-by-character with a visible delay, for
# video recordings where instant `fill`/`type` would look like a paste.
# playwright-cli's own `type` command uses page.keyboard.type() with 0ms
# delay — technically sequential key events, but visually indistinguishable
# from a paste at recording speed. This uses pressSequentially with an
# explicit delay instead.
#
# Usage:
#   type-slow.sh "<locator expression>" "text to type" [delay_ms] [session]
#
# <locator expression> is anything chainable off `page.`, e.g.:
#   "getByLabel('Username')"
#   "getByRole('textbox', { name: 'Password' })"
#   "getByTestId('crud-search-input')"
set -euo pipefail

LOCATOR="${1:?usage: type-slow.sh <locator-expr> <text> [delay_ms] [session]}"
TEXT="${2:?usage: type-slow.sh <locator-expr> <text> [delay_ms] [session]}"
DELAY="${3:-60}"
SESSION="${4:-}"

TMP_JS="$(mktemp /tmp/pw-type-slow-XXXXXX.js)"
trap 'rm -f "$TMP_JS"' EXIT

cat > "$TMP_JS" <<JS
async (page) => {
  await page.${LOCATOR}.pressSequentially(\`${TEXT}\`, { delay: ${DELAY} });
}
JS

if [ -n "$SESSION" ]; then
  playwright-cli -s="$SESSION" run-code --filename="$TMP_JS"
else
  playwright-cli run-code --filename="$TMP_JS"
fi
