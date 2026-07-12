#!/usr/bin/env bash
# Render a Playwright .webm screencast to a widely-playable .mp4.
#
#   ./render.sh recordings/entity-modals.webm [out.mp4]
#
# Playwright's webm is variable-framerate; we convert to constant 30fps H.264
# (yuv420p + faststart) so it plays everywhere and frame-accurate seeking works.
# The H.264 encoder is auto-detected: libx264 (best) -> libopenh264 (Fedora/RPM
# ffmpeg often ships this instead of x264) -> mpeg4 (last resort).
set -euo pipefail

SRC="${1:?usage: render.sh <input.webm> [output.mp4]}"
OUT="${2:-${SRC%.*}.mp4}"

# Capture the encoder list once — piping ffmpeg into `grep -q` would let grep
# close the pipe early (SIGPIPE) and, under `pipefail`, wrongly read as no-match.
ENCODERS="$(ffmpeg -hide_banner -encoders 2>/dev/null || true)"
if grep -q ' libx264' <<<"$ENCODERS"; then
  VCODEC=(-c:v libx264 -crf 20 -preset veryfast)
elif grep -q ' libopenh264' <<<"$ENCODERS"; then
  VCODEC=(-c:v libopenh264 -b:v 6M)
else
  VCODEC=(-c:v mpeg4 -q:v 3)
fi

echo "render: $SRC -> $OUT  (${VCODEC[*]})"
ffmpeg -y -i "$SRC" -vf "scale=1440:-2,fps=30" "${VCODEC[@]}" \
  -pix_fmt yuv420p -movflags +faststart "$OUT"
echo "done: $OUT"
