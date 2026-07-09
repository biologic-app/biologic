#!/usr/bin/env bash
# Render a Playwright demo: webm -> mp4 (CFR, web-safe), optional music mux.
# Usage:
#   ./render.sh <dir-with-page@*.webm> <out.mp4> [music.wav]
# Examples:
#   ./render.sh tmp/feat-demo tmp/feat-demo/demo.mp4
#   python3 make_funk.py /tmp/funk.wav 27 && ./render.sh tmp/feat-demo tmp/feat-demo/demo.mp4 /tmp/funk.wav
set -euo pipefail

DIR="${1:?dir with page@*.webm}"
OUT="${2:?output mp4 path}"
MUSIC="${3:-}"
WIDTH="${WIDTH:-1440}"
FPS="${FPS:-30}"

WEBM="$(find "$DIR" -maxdepth 1 -name 'page@*.webm' | head -1)"
[ -n "$WEBM" ] || { echo "no page@*.webm in $DIR" >&2; exit 1; }

ffmpeg -y -loglevel error -i "$WEBM" \
  -vf "scale=${WIDTH}:-2,fps=${FPS}" -c:v libx264 -pix_fmt yuv420p -movflags +faststart "$OUT"

if [ -n "$MUSIC" ]; then
  DUR="$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$OUT")"
  FADE_ST="$(awk "BEGIN{printf \"%.2f\", $DUR-1.5}")"
  MUSIC_OUT="${OUT%.mp4}-music.mp4"
  ffmpeg -y -loglevel error -i "$OUT" -i "$MUSIC" \
    -filter_complex "[1:a]afade=t=out:st=${FADE_ST}:d=1.5[a]" \
    -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -shortest "$MUSIC_OUT"
  echo "wrote $OUT and $MUSIC_OUT"
else
  echo "wrote $OUT"
fi
