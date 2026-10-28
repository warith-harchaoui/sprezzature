#!/usr/bin/env bash
#
# Render every cut the generator emits: eleven films, two languages, three
# canvases, all of them 4K. Sixty-six projects, about three and a half
# minutes each.
#
# Skips a project whose newest MP4 is younger than its index.html. A render is
# an expensive output of a cheap input, so it outlives the input: touch the
# generator and all sixty-six come back, touch one film's text and only its
# six cuts do. FORCE=1 re-renders everything regardless.
#
# Concurrency is `xargs -P`, not a hand-rolled job-slot loop. The first
# version of this script used `wait -n` to free a slot, which is bash 4 and
# this machine ships bash 3.2 — so every iteration printed "invalid option"
# and went straight on to the next, and sixty-six headless Chromes came up at
# once. The loop looked like it was throttling right up to the moment it was
# not.
#
# Usage
# -----
#     ./render_films.sh                # everything stale, one at a time
#     JOBS=2 ./render_films.sh         # two at a time
#     FORCE=1 ./render_films.sh maps   # one film, all six of its cuts
#
# Author
# ------
# Warith HARCHAOUI <warithmetics@deraison.ai>

set -u
cd "$(dirname "$0")/films" || exit 1

JOBS="${JOBS:-1}"
FORCE="${FORCE:-0}"
HF="hyperframes@0.8.46"

# Optional film keys: `./render_films.sh maps colors` takes those two only.
want_film() {
  [ "$#" -eq 1 ] && return 0          # no filter given
  local d="$1"; shift
  for key in "$@"; do
    case "$d" in "$key"-*) return 0 ;; esac
  done
  return 1
}

targets=()
for d in */; do
  d="${d%/}"
  [ -f "$d/index.html" ] || continue
  want_film "$d" "$@" || continue
  if [ "$FORCE" = 0 ]; then
    newest=$(ls -t "$d"/renders/*.mp4 2>/dev/null | head -1)
    [ -n "$newest" ] && [ "$newest" -nt "$d/index.html" ] && continue
  fi
  targets+=("$d")
done

total=${#targets[@]}
if [ "$total" -eq 0 ]; then
  echo "nothing to render; every cut is younger than its composition"
  exit 0
fi
echo "rendering $total project(s), $JOBS at a time"

# 4K, and the two flags that make it possible on this machine.
#
# `--resolution <canvas>-4k` leaves the composition alone and raises Chrome's
# device pixel ratio, so every cut is the same layout at four times the
# pixels: type stays crisp at a size somebody will actually watch it.
#
# `--low-memory-mode` is not about memory here, it is about disk. The default
# path writes all 1800 frames out before encoding, which at 3840x2160 wants
# ~60 GB of scratch; this machine has 32 GB free and the render dies at 25%
# naming the figure. Streaming encodes as it captures and needs almost none.
# It costs the parallel workers: 3m19s a cut instead of 38s.
# The project name arrives as an argument, not through `-I{}`. With `-I`,
# macOS xargs substitutes into the whole command line and then measures it
# against its own limit; a script this long blows that limit and xargs
# refuses the entire batch with "command line cannot be assembled, too long"
# -- after printing "rendering 66 project(s)", and before rendering any.
printf '%s\n' "${targets[@]}" | xargs -P "$JOBS" -n 1 sh -c '
  d="$1"
  case "$d" in
    *-portrait) res=portrait-4k ;;
    *-square)   res=square-4k ;;
    *)          res=landscape-4k ;;
  esac
  if (cd "$d" && npx --yes '"$HF"' render --quality looks \
        --resolution "$res" --low-memory-mode) >"$d.render.log" 2>&1; then
    printf "ok   %s (%s)\n" "$d" "$res"
  else
    printf "FAIL %s (films/%s.render.log)\n" "$d" "$d"
    exit 1
  fi
' _
rc=$?

# What came out, measured rather than assumed.
#
# Duration first: a killed render leaves a short MP4 behind, and
# `newest_render` would then pick it -- the install step would copy ten
# seconds of film over sixty and say nothing.
#
# Then the frame size, which is the check this script shipped without and
# needed on its first run. xargs refused the whole batch before rendering
# anything; every project still held its 1920x1080 cut from the pass before;
# the duration check found sixty-six files of sixty seconds each and printed
# "66/66 usable". A measurement that cannot tell the new output from the old
# one is not a check, it is a reassurance.
echo "checking what came out"
bad=0
for d in "${targets[@]}"; do
  newest=$(ls -t "$d"/renders/*.mp4 2>/dev/null | head -1)
  if [ -z "$newest" ]; then
    echo "MISSING $d"; bad=$((bad + 1)); continue
  fi
  secs=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$newest" 2>/dev/null)
  case "$secs" in
    59.*|60.*|6[01]) : ;;
    *) echo "SHORT   $d: ${secs:-unreadable}s — $newest"; bad=$((bad + 1)); continue ;;
  esac
  size=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height \
           -of csv=p=0:s=x "$newest" 2>/dev/null)
  case "$d:$size" in
    *-portrait:2160x3840|*-square:2160x2160) : ;;
    *-portrait:*|*-square:*)
      echo "NOT 4K  $d: $size — $newest"; bad=$((bad + 1)) ;;
    *:3840x2160) : ;;
    *) echo "NOT 4K  $d: $size — $newest"; bad=$((bad + 1)) ;;
  esac
done

echo "done: $((total - bad))/$total usable"
[ "$rc" -ne 0 ] && exit "$rc"
exit "$bad"
