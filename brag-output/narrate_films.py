#!/usr/bin/env python3
"""
Narrate the films through the suite's own voice, and let it write the cues.

What this replaced
------------------
Until 2026-10-26 the films were narrated by ``npx hyperframes tts`` — one
shell call per line, one WAV per line — and ``make_captions.py`` then built
the WebVTT by hand from durations measured with ``ffprobe``. Two things were
wrong with that, and only one of them was visible.

The visible one: hyperframes has no pronunciation lexicon, so a minute of
prose about this suite came out full of guesses. "WebVTT" was spelled in one
film and syllabified in the next; "GMTED2010" read its digits as a year;
"Sprezzature" was anglicised in the English cut. Every one of those is a word
the suite itself defines.

The invisible one: the caption track and the audio were produced by two
different pieces of arithmetic. ``make_captions.py`` computed cue boundaries
from measured durations and a hand-written splitter; the audio was a list of
files the film laid out at hard-coded times. Nothing made them agree. They did
agree — but by construction rather than by proof, and a construction holds
only as long as both halves are edited together.

So both jobs moved to ``sprezzature-audio``, which owns the sound modality in
both directions and owns the suite's single WebVTT writer. One call returns
the audio **and** the cues, laid out by the same timeline, and
``speaker-helper`` refuses a result whose timeline disagrees with its own
audio. The agreement is now checked rather than assumed.

Two passes, and why
-------------------
A film's lines start at times a scene grid dictates — 1.10 s, 6.50 s, 15.00 s
— and ``narrate`` lays segments out by pauses, not by absolute times. The
pause before line *n* is ``grid[n] - (grid[n-1] + duration[n-1])``, and the
duration is not known until the line has been spoken.

So: pass one with every pause at zero, purely to measure; then the pauses are
arithmetic; then pass two produces the deliverable. Kokoro is deterministic,
so the second pass speaks exactly what the first one measured. The cues it
returns are checked against the grid before anything is written, because a
2-pass layout that silently drifted would desynchronise every film at once.

The lead-in is not a pause
--------------------------
A narration starts when it starts: ``pause_before_ms`` on the *first* segment
is dropped, and the first cue lands at 0.000 whatever is asked for. That is
right for reading a page aloud and wrong for a film, whose first line is due
at 1.10 s. Asking for it anyway shifted every cue in every film by exactly
-1.100 s — a uniform offset, which is the kind that looks like a working
system until somebody reads a caption.

So the lead-in is the film's job: the track is placed at ``grid[0]`` and the
cues are shifted to match, through ``speaker_helper.cues_to_vtt`` — the same
writer that produced them. Shifted, not re-rendered: there is one WebVTT
writer in this suite and a second one here would be the drift it exists to
prevent.

Usage
-----
    python3 narrate_films.py                 # every film, both languages
    python3 narrate_films.py ui colors       # just these
    python3 narrate_films.py --lang fr       # just the French cuts

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from make_captions import FILMS  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent
ASSETS = ROOT / "_assets"
VIDEO = ROOT.parent / "web" / "video"
LEXICON = ROOT / "lexicon.yaml"

#: The engine, and the voice per language. Kokoro in both, deliberately.
#:
#: `speaker-helper` 0.11 ships a router that would pick kyutai for offline
#: French, and it is right about speech: kyutai renders French natively where
#: kokoro reaches it through an English-first pipeline. Two reasons not to
#: take it here. It is the suite's own shop window, so it should demonstrate
#: what `pip install sprezzature-audio[narrate]` gives a reader — kyutai is an
#: extra, because its weights are CC-BY-4.0 and this suite's bar is Apache-2.0
#: in code *and* weights. And the English and French cuts of one film are a
#: pair: one engine for both makes them sound like siblings, which two engines
#: with different training would not.
#:
#: Both voices are female, which is `speaker-helper`'s contract in every
#: language and not an accident of the defaults.
ENGINE = "kokoro"
VOICE = {"en": "af_heart", "fr": "ff_siwis"}

#: How far a laid-out cue may sit from the grid time the film expects.
#: Generous by audio standards and tight by film ones: a frame at 30 fps is
#: 33 ms, so anything inside this is inside a frame.
TOLERANCE_S = 0.030


def _narrate(segments: list[dict], lang: str, out_dir: pathlib.Path) -> dict:
    """One pass of the engine, with the lexicon applied."""
    import sprezzature_audio

    return sprezzature_audio.narrate(
        ENGINE,
        segments,
        voice=VOICE[lang],
        voice_sample=None,
        out_dir=out_dir,
        lang=lang,
        lexicon=LEXICON,
    )


def _cues(vtt: pathlib.Path) -> list[tuple[float, float]]:
    """Start and end of every cue, in seconds, read back off the WebVTT.

    Read off the file rather than taken from the result object on purpose:
    the file is what a player will use, so the file is what gets checked. A
    rounding difference between the two would otherwise hide here.
    """
    out: list[tuple[float, float]] = []
    for line in vtt.read_text(encoding="utf-8").splitlines():
        if "-->" not in line:
            continue
        a, b = (part.strip() for part in line.split("-->"))
        out.append((_seconds(a), _seconds(b)))
    return out


def _seconds(stamp: str) -> float:
    h, m, s = stamp.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def narrate_film(film: str, lang: str, *, quiet: bool = False) -> list[str]:
    """Write one film's voice track and its cues. Returns problem lines."""
    lines = FILMS[film][lang]
    grid = [start for start, _dur, _text in lines]
    texts = [text for _start, _dur, text in lines]

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = pathlib.Path(tmp)

        # Pass one: measure. Every pause zero, so a cue's length is the line's
        # length and nothing else.
        flat = [{"text": t, "pause_before_ms": 0, "pause_after_ms": 0} for t in texts]
        report = _narrate(flat, lang, tmpdir)
        measured = [end - start for start, end in _cues(pathlib.Path(report["cues"]))]
        if len(measured) != len(texts):
            return [
                f"  {film}.{lang}: {len(texts)} lines went in and {len(measured)} "
                f"cues came back. A line was split or dropped, and the grid "
                f"arithmetic below assumes one cue per line."
            ]

        # The pauses that put each line on its mark, relative to the first.
        # The first pause is zero because it would be dropped anyway; the
        # film carries that silence instead, by placing the track at grid[0].
        lead_in = grid[0]
        pauses: list[int] = []
        cursor = lead_in
        for want, dur in zip(grid, measured):
            pauses.append(max(0, round((want - cursor) * 1000)))
            cursor = want + dur

        # Pass two: the deliverable.
        laid = [
            {"text": t, "pause_before_ms": p, "pause_after_ms": 0}
            for t, p in zip(texts, pauses)
        ]
        report = _narrate(laid, lang, tmpdir)
        got = [
            (start + lead_in, end + lead_in)
            for start, end in _cues(pathlib.Path(report["cues"]))
        ]

        problems: list[str] = []
        for n, ((start, end), want) in enumerate(zip(got, grid), 1):
            if abs(start - want) > TOLERANCE_S:
                problems.append(
                    f"  {film}.{lang} line {n}: laid out at {start:.3f}s, the "
                    f"film expects {want:.3f}s (off by {start - want:+.3f}s)"
                )
            if n < len(grid) and end > grid[n] + TOLERANCE_S:
                problems.append(
                    f"  {film}.{lang} line {n}: runs to {end:.3f}s, over line "
                    f"{n + 1} which starts at {grid[n]:.3f}s"
                )
        last_end = got[-1][1] if got else 0.0
        if last_end > 60.0:
            problems.append(
                f"  {film}.{lang}: the last line ends at {last_end:.3f}s, past "
                f"the film's 60 s"
            )
        if problems:
            return problems

        ASSETS.mkdir(parents=True, exist_ok=True)
        VIDEO.mkdir(parents=True, exist_ok=True)
        wav = ASSETS / f"vo-{film}.{lang}.wav"
        vtt = VIDEO / f"{film}.{lang}.vtt"
        wav.write_bytes(pathlib.Path(report["audio"]).read_bytes())
        vtt.write_text(_vtt(texts, got), encoding="utf-8")
        if not quiet:
            print(
                f"  {film}.{lang}: {len(texts)} lines, lead-in {lead_in:.2f}s, "
                f"{report['duration_seconds']:.3f}s of voice, {VOICE[lang]} "
                f"-> {wav.name} + {vtt.name}"
            )
    return []


def _vtt(texts: list[str], times: list[tuple[float, float]]) -> str:
    """The cues, shifted onto the film's clock, through the suite's writer.

    Rebuilt rather than string-edited: the timestamps are the library's
    format, the identifiers are its segment indices, and a regex over its
    output would be a second implementation of a format this suite has
    deliberately reduced to one.
    """
    from speaker_helper import SpeechCue, cues_to_vtt

    return cues_to_vtt(
        [
            SpeechCue(index=i, text=t, start_seconds=a, end_seconds=b)
            for i, (t, (a, b)) in enumerate(zip(texts, times))
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n")[1],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("films", nargs="*", help="Film keys; default is all of them.")
    parser.add_argument(
        "--lang", choices=("en", "fr"), action="append",
        help="Language to narrate; repeatable. Default: both.",
    )
    args = parser.parse_args()

    if not LEXICON.is_file():
        sys.stderr.write(f"no lexicon at {LEXICON}\n")
        return 2

    import sprezzature_audio

    if sprezzature_audio.check_narration_install(ENGINE) != 0:
        sys.stderr.write(
            f"{ENGINE} cannot synthesise here.\n"
            f"    pip install 'sprezzature-audio[narrate]'\n"
            f"    brew install espeak-ng\n"
        )
        return 2

    # The three eighteen-second group films are retired and not re-cut.
    wanted = args.films or [k for k, v in FILMS.items() if len(v["en"]) >= 8]
    langs = args.lang or ["en", "fr"]

    problems: list[str] = []
    for film in wanted:
        if film not in FILMS:
            problems.append(f"  no such film: {film}")
            continue
        for lang in langs:
            problems += narrate_film(film, lang)

    if problems:
        sys.stderr.write("\n".join(problems) + "\n")
        return 1
    print(f"{len(wanted)} film(s) x {len(langs)} language(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
