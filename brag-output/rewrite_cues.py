#!/usr/bin/env python3
"""
Re-emit a shipped caption track under the current cue rule, without narrating.

Why this exists, and why it is not `narrate_films.py`
-----------------------------------------------------
`narrate_films.py` is the right tool when the *words* changed: it speaks them,
measures the audio, and writes the voice and the cues from one timeline. It
costs a full synthesis per line, and `chatterbox` is not deterministic, so a
re-narration returns a different voice track even when the script is identical.

When only the **cue rule** changed, none of that is wanted. The words that were
spoken are in the track, the speech timings are in the track, and the thing to
redo is the part that never touched the audio: where the lines break, and how
long each cue holds the screen. That is what this does. The WAV is not opened.

It is the repair of 2026-10-31. The 22 shipped tracks carried 393 findings
against `sprezzature-audio-audit` — 360 lines over the 42-character budget, 27
cues over the 17-characters-a-second ceiling, 6 holding the screen past 7
seconds. None of it was a stale *rule*: `make_captions.wrap_cue` had wrapped at
42 since 2026-10-29. The breaks were being written and then removed, because
the cues went out through a writer that collapses the payload. The tracks had
simply never been re-emitted since. See `make_captions.timed_cues`.

Idempotent on purpose: a track already under the rule comes back byte for byte,
so this is safe to run over everything and safe to run twice. `--check` asserts
exactly that and writes nothing, which is what a guard can call.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
VIDEO = ROOT / "web" / "video"


def rewritten(track: Path) -> str:
    """One track's WebVTT, re-emitted under the current rule.

    The cues are read with `sprezzature_audio.parse` — the reader that feeds
    the auditor, so what this writes and what the audit measures are the same
    two ends of one library.
    """
    from sprezzature_audio import parse

    from make_captions import render_cues, timed_cues

    cues = parse(track.read_text(encoding="utf-8"))
    # The text is re-joined before it goes back in: a track already under the
    # rule carries the newline this put there, and `timed_cues` wraps from the
    # spoken line, not from a previous wrapping of it. Without this the second
    # run would wrap an already-wrapped line and the result would depend on how
    # many times the script had been run.
    texts = [" ".join(cue.text.split()) for cue in cues]
    times = [(cue.start, cue.end) for cue in cues]
    return render_cues(timed_cues(texts, times))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument(
        "tracks",
        nargs="*",
        type=Path,
        help="Tracks to re-emit; default is every web/video/*.vtt.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Write nothing; exit 1 if any track is not already under the rule.",
    )
    args = parser.parse_args()

    tracks = args.tracks or sorted(VIDEO.glob("*.vtt"))
    if not tracks:
        sys.stderr.write(f"no caption tracks under {VIDEO}\n")
        return 1

    stale: list[str] = []
    changed = 0
    for track in tracks:
        before = track.read_text(encoding="utf-8")
        after = rewritten(track)
        if before == after:
            continue
        if args.check:
            stale.append(track.name)
            continue
        track.write_text(after, encoding="utf-8")
        changed += 1
        print(f"  rewrote {track.name}")

    if args.check:
        if stale:
            sys.stderr.write(
                f"{len(stale)} track(s) not under the current cue rule: "
                f"{', '.join(stale)}\n"
                f"run `python3 brag-output/rewrite_cues.py` to re-emit them.\n"
            )
            return 1
        print(f"{len(tracks)} track(s) already under the cue rule")
        return 0

    print(f"{changed} of {len(tracks)} track(s) rewritten")
    return 0


if __name__ == "__main__":
    sys.exit(main())
