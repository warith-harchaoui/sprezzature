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

Where the lines land is then `sprezzature_video.timeline.lay_out`, and the
grid in `make_captions` is a *request* rather than a constraint: a line starts
at the later of the scene it was written for and the moment the line in front
of it stops. Until 2026-10-28 an overrun was a refusal, and the refusal is
what left fourteen cuts out of twenty-two carrying a voice older than their
script for days — the build neither broke nor advanced. Now a line that
overruns pushes the next one, the drift is printed, and the only thing still
fatal is the one no layout absorbs: a script that does not fit in sixty
seconds.

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
import hashlib
import json

import pathlib
import re
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from make_captions import FILMS  # noqa: E402

from sprezzature_video.timeline import lay_out  # noqa: E402

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
#: kyutai itself was dropped on 2026-11-01: `sprezzature-audio` 1.8.0 removed
#: the wrapper, the console script and the `[narrate-kyutai]` extra. It stays
#: in `speaker-helper`'s catalogue, where the engine list belongs, and the
#: router never answered it -- swept over five conditions and five languages
#: the answer was chatterbox everywhere it answered at all.
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
    """The engine and voice for one language, decided by `speaker-helper`.

    The router is consulted every time rather than once at import: which
    engine speaks a language is a fact about the installed `speaker-helper`,
    and reading it at call time is how an upgrade reaches these films without
    anyone editing this file. It reached them twice in one day.

    Nothing is kept back from it
    ----------------------------
    Between 2026-10-28 and 2026-10-29 this function held one exception: a
    language the router had not ratified kept the engine these films had been
    narrated with, which in practice meant English stayed on kokoro while
    French had moved to chatterbox. The exception is gone, and the reasoning
    behind it was wrong twice over.

    It was wrong about whose decision this is. `speaker-helper` is the brick
    that arbitrates voices for this suite; a caller that keeps its own copy of
    the answer is the exact defect this audit keeps turning up, and a
    *conditional* copy is the worst version of it, because it agrees with the
    router right up until the moment the two differ.

    It was also wrong to reach for cost. The pinned engine ran near real time
    and the routed one runs at a real-time factor between four and eight, so
    the exception bought hours. Hours are not an argument. A film carries the
    voice the suite chose, and what that costs to synthesise is not a reason
    to ship a different one.

    What the router answers today is chatterbox in both languages, ratified
    for French and not yet for English, and the two are obeyed alike. The
    variant is chatterbox's own call, made inside the backend from the
    language: Turbo reads English, Multilingual reads the rest.
    """
    from speaker_helper import RouteRequest, route

    engine = route(RouteRequest(condition="offline", language=lang)).engine
    return engine, VOICES.get(engine, {}).get(lang, "")


#: How long each of these films is, asked of the module that declares them.
#:
#: It was a literal here until 2026-10-29, and the literal was `60.0` on the
#: morning the films went to 117 s. Two copies of one number is how a layout
#: silently refuses a script that fits: everything in `lay_out` gives except
#: the duration, so the wrong duration is the one error that cannot be
#: absorbed. The number has one owner now, and this module reads it.
from build_films import DURATION_S  # noqa: E402


#: The voice is heard back before it is kept. Measured on 2026-11-06 through
#: the suite's own transcriber, the set before carried "Esprit Tatouré" for
#: the name, "expresser.ai" for the address, "1, 1, 51, 1 contre 1" for a
#: ratio, and one closing line spoken twice. Chatterbox samples, so a bad
#: take is usually a bad *draw*: the same line spoken again comes out right.
#: Each line is transcribed with no vocabulary hint (a hint would hear the
#: word it was told to expect) and compared with the script; a take under
#: ACCEPT is drawn again, up to MAX_TAKES, and the best one is kept.
ACCEPT = 0.88
MAX_TAKES = 4

#: Takes that passed the gate, one per (language, voice, spoken text). A film
#: whose closing line changes is then one synthesis, not fourteen: at an RTF
#: near eight that is the difference between minutes and an afternoon. Kept
#: outside the repo because it only saves time; deleting it costs nothing but
#: the time.
TAKES_CACHE = pathlib.Path.home() / ".cache" / "sprezzature-films" / "takes"


def _cached_take(text: str, lang: str) -> pathlib.Path:
    engine, voice = voice_of(lang)
    key = hashlib.sha256(f"{lang}\0{engine}\0{voice}\0{text}".encode()).hexdigest()[:24]
    return TAKES_CACHE / f"{key}.wav"

#: The name, however a transcriber spells what it heard: "Spretsatoorey",
#: "Sprettsatour", "Sprzzature". Matched on the sound's skeleton.
_BRAND = re.compile(r"\bs\s?p\s?r\w*?(?:t+s|z+|tz)\w*?t[ou]+r\w*", re.I)


_EN = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
_EN_T = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
_FR = "zéro un deux trois quatre cinq six sept huit neuf dix onze douze treize quatorze quinze seize dix-sept dix-huit dix-neuf".split()
_FR_T = "_ _ vingt trente quarante cinquante soixante".split()


def _en(n: int) -> str:
    if n < 20:
        return _EN[n]
    if n < 100:
        return _EN_T[n // 10] + ("-" + _EN[n % 10] if n % 10 else "")
    rest = n % 100
    return _EN[n // 100] + " hundred" + (" and " + _en(rest) if rest else "")


def _fr(n: int) -> str:
    if n < 20:
        return _FR[n]
    if n < 70:
        t, u = divmod(n, 10)
        return _FR_T[t] + ("-et-un" if u == 1 else ("-" + _FR[u] if u else ""))
    if n < 80:
        return "soixante" + ("-et-" if n == 71 else "-") + _FR[n - 60]
    if n < 100:
        return "quatre-vingt" + ("-" + _FR[n - 80] if n > 80 else "s")
    h, rest = divmod(n, 100)
    head = "cent" if h == 1 else _FR[h] + " cent" + ("s" if not rest else "")
    return head + (" " + _fr(rest) if rest else "")


def _spoken(text: str, lang: str) -> str:
    """The line as the engine should read it: every count in words.

    The script, the screen and the captions keep digits (the owner's rule of
    2026-10-29: a count is read in one fixation as a digit). The engine never
    sees one, because it reads them badly: "167" came back as "Tuscan", "22"
    as "Zan 2". Small whole numbers only, which is all the films hold.
    """
    words = _en if lang == "en" else _fr
    return re.sub(r"\b\d{1,3}\b", lambda m: words(int(m.group())), text)


def _heard(clip: pathlib.Path, lang: str) -> str:
    """What the suite's transcriber hears in one clip, unprompted."""
    import subprocess

    out = clip.with_suffix(".heard.txt")
    subprocess.run(
        ["sprezzature-audio", "captions", str(clip), "--format", "text", "--lang", lang,
         "--out", str(out), "--no-cache"],
        capture_output=True, check=False,
    )
    return out.read_text(encoding="utf-8").strip() if out.is_file() else ""


def _words(text: str) -> list[str]:
    import unicodedata

    text = _BRAND.sub(" sprezzature ", text)
    text = text.replace("\u2019", "'").lower()
    text = re.sub(r"\bd'ia\b|\bdia\b", "d ia", text)
    text = "".join(c if (c.isalnum() or c in " '") else " " for c in unicodedata.normalize("NFC", text))
    return [w for w in re.split(r"[\s']+", text) if w]


def _match(script: str, heard: str, seconds: float) -> float:
    """How closely a take says its line: word overlap, zero for a runaway take.

    A take far longer than its words is the other chatterbox failure: the line
    said, then a second of babble or the line again. Fifteen characters a
    second is a brisk read; under five means something was added.
    """
    import difflib

    if seconds > 1.5 and len(script) / seconds < 5.0:
        return 0.0
    a, b = _words(script), _words(heard)
    if not a or not b:
        return 0.0
    score = difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()
    # The name is the one word a viewer certainly notices, and one wrong word
    # in eight still scores 0.88. So it is held separately: the Italian "tts"
    # has to be heard ("Splesaturé" passed on overlap alone).
    if "sprezzature" in a and "sprezzature" not in b:
        score = min(score, 0.5)
    return score


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


def _assemble(
    clips: list[pathlib.Path], starts: list[float], dest: pathlib.Path
) -> None:
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
                    params.framerate,
                    params.sampwidth,
                    params.nchannels,
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
        takes_log: list[dict] = []
        for n, text in enumerate(texts, 1):
            best = None
            cached = _cached_take(_spoken(text, lang), lang)
            if cached.exists():
                meta = json.loads(cached.with_suffix(".json").read_text())
                best = (meta["score"], cached, meta["heard"], 0)
                if not quiet:
                    print(f"    {film}.{lang} line {n} cached: {best[0]:.2f}  {best[2]!r}", flush=True)
            for take in range(1, MAX_TAKES + 1 if best is None else 1):
                report = _narrate(
                    [{"text": _spoken(text, lang), "pause_before_ms": 0, "pause_after_ms": 0}],
                    lang,
                    tmpdir / f"line-{n:02d}-take-{take}",
                )
                clip = pathlib.Path(report["audio"])
                heard = _heard(clip, lang)
                score = _match(_spoken(text, lang), _spoken(heard, lang), _wav_seconds(clip))
                if not quiet:
                    print(f"    {film}.{lang} line {n} take {take}: {score:.2f}  {heard!r}", flush=True)
                if best is None or score > best[0]:
                    best = (score, clip, heard, take)
                if score >= ACCEPT:
                    break
            if best[0] >= ACCEPT and best[1] != cached:
                TAKES_CACHE.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(best[1], cached)
                cached.with_suffix(".json").write_text(
                    json.dumps({"text": text, "heard": best[2], "score": round(best[0], 3)}, ensure_ascii=False)
                )
            clips.append(best[1])
            takes_log.append(
                {"line": n, "text": text, "heard": best[2], "score": round(best[0], 3), "take": best[3]}
            )

        spoken = [_wav_seconds(clip) for clip in clips]

        # Where each line lands is arithmetic over lengths already on disk,
        # done by the brick that owns films rather than here. The grid in
        # `make_captions` is a *request* -- the scene each line was written
        # for -- and `lay_out` honours it unless the line in front has not
        # finished, in which case the line is pushed rather than the build
        # refused. That refusal is what left fourteen cuts out of twenty-two
        # carrying a voice older than their script: correct, and stuck.
        layout = lay_out(grid, spoken, duration=DURATION_S, texts=texts)
        if not layout.fits:
            # The one failure no layout absorbs: a script too long for its
            # film. Reported with the measured lengths, so a caller cutting
            # words does not have to synthesise the film again to find out
            # which line to cut.
            return [f"  {film}.{lang}: {line}" for line in layout.report()] + [
                f"  {film}.{lang} measured: "
                + " ".join(f"{length:.3f}" for length in spoken)
            ]

        ASSETS.mkdir(parents=True, exist_ok=True)
        VIDEO.mkdir(parents=True, exist_ok=True)
        wav = ASSETS / f"vo-{film}.{lang}.wav"
        vtt = VIDEO / f"{film}.{lang}.vtt"
        _assemble(clips, [start - lead_in for start in layout.starts], wav)
        vtt.write_text(
            _vtt(texts, [(line.start, line.end) for line in layout.lines]),
            encoding="utf-8",
        )
        _stamp(film, lang, len(texts))
        import json as _json

        (ASSETS / f"vo-{film}.{lang}.takes.json").write_text(
            _json.dumps(takes_log, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        weak = [t for t in takes_log if t["score"] < ACCEPT]
        for t in weak:
            print(f"    WEAK {film}.{lang} line {t['line']} ({t['score']:.2f}): {t['heard']!r}")
        if not quiet:
            print(
                f"  {film}.{lang}: {len(texts)} lines, lead-in {lead_in:.2f}s, "
                f"{_wav_seconds(wav):.3f}s of track, {voice_of(lang)[0]} "
                f"-> {wav.name} + {vtt.name}"
            )
            # Drift is a note, not a failure: a line that lands half a second
            # after the picture it describes is worth eight fewer words next
            # time, and is not worth refusing a four-hour narration over.
            for line in layout.report():
                print(f"    note: {line}")
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

    Both the wrapping and the cue timing live in `make_captions.timed_cues`,
    which is also what re-emits an existing track. The writer is
    `sprezzature-audio`, not `speaker-helper`: see that function for the
    measurement that moved it, and for why a cue is allowed to hold the screen
    into the pause after it.
    """
    from make_captions import render_cues, timed_cues

    return render_cues(timed_cues(texts, times))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n")[1],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("films", nargs="*", help="Film keys; default is all of them.")
    parser.add_argument(
        "--lang",
        choices=("en", "fr"),
        action="append",
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

    # Asked per language even though the router answers chatterbox for both
    # today, because that is an answer and not a guarantee: the next version
    # of speaker-helper may separate them again, and a check that ran once
    # would pass on a machine able to speak only the language it happened to
    # ask about.
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
