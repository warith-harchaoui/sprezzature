#!/usr/bin/env bash
# Ralph Eyeball Loop for web pages — render a local HTML file to a PNG,
# then look at the result and refine the source.
#
# Usage:
#   scripts/render_web.sh web/index.html [out.png] [width] [height]
#
# Defaults: width=1440, height=900 (desktop viewport).
# A second pass at 375x812 (mobile) is recommended before shipping.
#
# Loop:
#   1. render  — this script produces a PNG
#   2. look    — open the PNG and critique layout, hierarchy, spacing,
#                contrast, above-the-fold content, dark mode
#   3. refine  — edit the HTML/CSS
#   4. repeat  — until satisfied at both desktop and mobile sizes
#   5. gate    — run lint_a11y.py on the file before committing
#
# Example full loop:
#   scripts/render_web.sh web/index.html .private/screenshots/home-desktop.png
#   scripts/render_web.sh web/index.html .private/screenshots/home-mobile.png 375 812
#   python3 sprezzature-accessibility/scripts/lint_a11y.py web/index.html
set -euo pipefail

SRC="${1:?Usage: $0 <html-file> [out.png] [width] [height]}"
BASENAME=$(basename "$SRC" .html)
OUT="${2:-.private/screenshots/${BASENAME}-$(date +%Y%m%d-%H%M%S).png}"
W="${3:-1440}"
H="${4:-900}"

mkdir -p "$(dirname "$OUT")"

# Try to find Chrome / Chromium
CHROME=""
for candidate in \
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    "/Applications/Chromium.app/Contents/MacOS/Chromium" \
    google-chrome chromium chromium-browser; do
  if command -v "$candidate" &>/dev/null 2>&1 || [ -x "$candidate" ]; then
    CHROME="$candidate"
    break
  fi
done

if [ -z "$CHROME" ]; then
  echo "render_web: Chrome / Chromium not found. Install Google Chrome." >&2
  exit 1
fi

ABS_SRC="$(cd "$(dirname "$SRC")" && pwd)/$(basename "$SRC")"

# Headless Chrome enforces a ~500px minimum window width: a narrower request is
# laid out at ~485px and then cropped, faking a horizontal-overflow bug. Clamp
# up to 500 and warn. --hide-scrollbars makes the CSS viewport == window width.
if [ "$W" -lt 500 ]; then
  echo "render_web: width ${W} is below Chrome's ~500px headless minimum; rendering at 500 (large-phone). For a true 375px phone, use a browser's device-mode." >&2
  W=500
fi

"$CHROME" \
  --headless=new \
  --screenshot="$OUT" \
  --window-size="${W},${H}" \
  --hide-scrollbars \
  --no-sandbox \
  "file://${ABS_SRC}" 2>/dev/null

echo "render_web: wrote ${OUT}  (${W}×${H})"
echo "Look at it, critique, edit ${SRC}, then re-run."
