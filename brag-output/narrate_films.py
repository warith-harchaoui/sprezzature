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

One line at a time, and why
---------------------------
A film's lines start at times a scene grid dictates — 1.10 s, 6.50 s, 15.00 s
— and ``narrate`` lays segments out by pauses, not by absolute times. The
pause before line *n* is ``grid[n] - (grid[n-1] + duration[n-1])``, and the
duration is not known until the line has been spoken.

This used to be two passes: one with every pause at zero, purely to measure,
then the pauses were arithmetic, then a second pass produced the deliverable.
That rested on one sentence — "Kokoro is deterministic, so the second pass
speaks exactly what the first one measured" — and the sentence stopped being
true on 2026-10-28, when `speaker-helper` 0.13 sent offline narration to
chatterbox in every language.

Chatterbox samples. The same French line, spoken three times, measured 7.520,
6.760 and 6.640 seconds, and one run of the whole set produced a line of
roughly twenty-five seconds where the others gave seven. A layout computed
from pass one is therefore wrong for pass two by up to a second, at random,
and the check at the end would have caught it as an off-grid cue — a build
that fails on a different film every time it is run.

So the deliverable is the audio that was measured: each line is spoken once,
its WAV kept, its length read off that file, and the track is assembled from
those exact clips with silence between them. The layout is arithmetic over
lengths already on disk, so it cannot drift from what the engine produced. It
also halves the synthesis, which matters when the engine runs at an RTF of
eight.

What is still checked is what assembly cannot fix: a line longer than the gap
before the next one, and a last line running past the film's sixty seconds.

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

#: Which engine reads which language is asked of `speaker-helper`, not decided
#: here. It was decided here until 2026-10-28 -- ``ENGINE = "kokoro"`` and a
#: voice per language -- and the reasoning was sound at the time: one engine
#: for both cuts of a film makes them sound like siblings, and kyutai, which
#: the 0.11 router preferred for offline French, ships CC-BY-4.0 weights where
#: this suite's bar is Apache-2.0 in code *and* weights.
#:
#: `speaker-helper` 0.12 and 0.13 settled it twice over. 0.12 made offline
#: French the owner's **ratified** choice of chatterbox, carried by the router
#: and flagged ``owner_ratified``. 0.13 made the default path follow the same
#: matrix in every language: offline is chatterbox everywhere (Turbo for
#: English, Multilingual elsewhere), streaming is kokoro.
#:
#: So there is nothing left for a constant here to hold. A pinned engine in
#: the suite's own films would be a second opinion about the suite's own
#: voice, which is the shape of every defect this audit has turned up: the
#: tool exists, and the caller keeps its own copy of the answer.
#:
#: The one thing still decided here is the voice *name*, because an engine
#: wants different things by nature: kokoro reads with one of 54 named voices,
#: chatterbox renders from a reference recording and takes ``""`` for its own.
#: Both are female, which is `speaker-helper`'s contract in every language.
VOICES: dict[str, dict[str, str]] = {
    "kokoro": {"en": "af_heart", "fr": "ff_siwis"},
    "chatterbox": {"en": "", "fr": ""},
}


def voice_of(lang: str) -> tuple[str, str]:
    """The engine and voice for one language, asked of `speaker-helper`.

    The router is consulted every time rather than once at import: which
    engine speaks a language is a fact about the installed `speaker-helper`,
    and reading it at call time is how an upgrade reaches these films without
    anyone editing this file. It reached them twice in one day.
    """
    from speaker_helper import RouteRequest, route

    engine = route(RouteRequest(condition="offline", language=lang)).engine
    return engine, VOICES.get(engine, {}).get(lang, "")


#: How far a laid-out cue may sit from the grid time the film expects.
#: Generous by audio standards and tight by film ones: a frame at 30 fps is
#: 33 ms, so anything inside this is inside a frame.
TOLERANCE_S = 0.030


def _narrate(segments: list[dict], lang: str, out_dir: pathlib.Path) -> dict:
    """One pass of the engine, with the lexicon applied."""
    import sprezzature_audio

    engine, voice = voice_of(lang)
    return sprezzature_audio.narrate(
        engine,
        segments,
        voice=voice,
        voice_sample=None,
        out_dir=out_dir,
        lang=lang,
        lexicon=LEXICON,
    )


def _wav_seconds(path: pathlib.Path) -> float:
    """How long a WAV actually is, read off the file.

    Not the engine's reported ``duration_seconds``: the file is what gets
    assembled and what a player will time against, so the file is what the
    arithmetic uses.
    """
    import wave

    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / handle.getframerate()


def _assemble(clips: list[pathlib.Path], starts: list[float], dest: pathlib.Path) -> None:
    """Lay the spoken clips on one timeline, silence between them.

    ``starts`` are seconds from the beginning of the track, so the caller has
    already taken the lead-in off the film's clock. Silence is written as
    zeroed frames in the clips' own format, which is why the formats are
    compared rather than assumed: a mismatch would produce a file that plays
    at the wrong speed from the first mismatched clip onward, and nothing
    downstream would say so.
    """
    import wave

    with wave.open(str(clips[0]), "rb") as first:
        params = first.getparams()

    frame = params.sampwidth * params.nchannels
    with wave.open(str(dest), "wb") as out:
        out.setparams(params)
        cursor = 0  # frames written so far
        for clip, start in zip(clips, starts):
            with wave.open(str(clip), "rb") as handle:
                here = handle.getparams()
                if (here.framerate, here.sampwidth, here.nchannels) != (
                    params.framerate, params.sampwidth, params.nchannels
                ):
                    raise ValueError(
                        f"{clip.name} is {here.framerate}Hz/{here.sampwidth}B/"
                        f"{here.nchannels}ch where the first clip is "
                        f"{params.framerate}Hz/{params.sampwidth}B/{params.nchannels}ch"
                    )
                want = round(start * params.framerate)
                if want > cursor:
                    out.writeframes(b"\x00" * ((want - cursor) * frame))
                    cursor = want
                out.writeframes(handle.readframes(handle.getnframes()))
                cursor += handle.getnframes()


def narrate_film(film: str, lang: str, *, quiet: bool = False) -> list[str]:
    """Write one film's voice track and its cues. Returns problem lines."""
    lines = FILMS[film][lang]
    grid = [start for start, _dur, _text in lines]
    texts = [text for _start, _dur, text in lines]
    lead_in = grid[0]

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = pathlib.Path(tmp)

        # One call per line, each into its own directory: the engine writes
        # ``narration.wav`` by name, so a shared directory would leave every
        # line but the last on the floor.
        clips: list[pathlib.Path] = []
        for n, text in enumerate(texts, 1):
            report = _narrate(
                [{"text": text, "pause_before_ms": 0, "pause_after_ms": 0}],
                lang,
                tmpdir / f"line-{n:02d}",
            )
            clips.append(pathlib.Path(report["audio"]))

        spoken = [_wav_seconds(clip) for clip in clips]
        got = [(want, want + length) for want, length in zip(grid, spoken)]

        # Every cue is on its mark by construction now, so the only thing left
        # to check is whether the line fits in the room the film gives it.
        problems: list[str] = []
        for n, ((_start, end), _want) in enumerate(zip(got, grid), 1):
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
            # The measured lengths, so a caller fixing the grid does not have
            # to synthesise the film again to find out what it asked for.
            problems.append(
                f"  {film}.{lang} measured: "
                + " ".join(f"{length:.3f}" for length in spoken)
            )
            return problems

        ASSETS.mkdir(parents=True, exist_ok=True)
        VIDEO.mkdir(parents=True, exist_ok=True)
        wav = ASSETS / f"vo-{film}.{lang}.wav"
        vtt = VIDEO / f"{film}.{lang}.vtt"
        _assemble(clips, [want - lead_in for want in grid], wav)
        vtt.write_text(_vtt(texts, got), encoding="utf-8")
        _stamp(film, lang, len(texts))
        if not quiet:
            print(
                f"  {film}.{lang}: {len(texts)} lines, lead-in {lead_in:.2f}s, "
                f"{_wav_seconds(wav):.3f}s of track, {voice_of(lang)[0]} "
                f"-> {wav.name} + {vtt.name}"
            )
    return []


def _stamp(film: str, lang: str, lines: int) -> None:
    """Record which voice spoke this track, beside the track.

    Nothing in a WAV or a WebVTT says who read it. The freshness guard
    compares the cues with the script, which catches a line that was rewritten
    and never re-spoken and is blind to the other half: a line that is word
    for word correct and was read by an engine the suite no longer chooses.

    That happened the day it was written. `speaker-helper` 0.12 ratified
    chatterbox for offline French, and five French tracks went on passing the
    freshness guard while kokoro's voice was still in them. A mixed set is the
    kind of defect nobody sees in a diff and everybody hears in the second
    film they watch.

    Written next to the cues rather than next to the audio on purpose:
    `_assets/` is the tree `restore_assets.py` counts, and the `video` film
    puts that count on screen.
    """
    import json

    from speaker_helper import __version__ as speaker_helper_version

    engine, voice = voice_of(lang)
    (VIDEO / f"{film}.{lang}.voice.json").write_text(
        json.dumps(
            {
                "engine": engine,
                "voice": voice,
                "speaker_helper": speaker_helper_version,
                "lines": lines,
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )


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

    # The three eighteen-second group films are retired and not re-cut.
    wanted = args.films or [k for k, v in FILMS.items() if len(v["en"]) >= 8]
    langs = args.lang or ["en", "fr"]

    # Asked per language, because they no longer share an engine: the router
    # carries the owner's ratified choice for French and the films pin
    # English. Checking only one of them would pass on a machine that can
    # speak the other.
    for lang in langs:
        engine, _voice = voice_of(lang)
        if sprezzature_audio.check_narration_install(engine) != 0:
            sys.stderr.write(
                f"{engine}, which reads {lang}, cannot synthesise here.\n"
                f"    pip install 'sprezzature-audio[narrate,narrate-{engine}]'\n"
                f"    brew install espeak-ng\n"
            )
            return 2
        print(f"{lang}: {engine}" + (f" / {_voice}" if _voice else ""), file=sys.stderr)

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
