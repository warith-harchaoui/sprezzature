"""
A film's voice says what its caption track says.

How two films went a day with the wrong voice
---------------------------------------------
``narrate_films.py`` lays each line out against the film's beat grid and
refuses the result if a line overruns the start of the next one. That check
is right, and the way it fails is not: it prints to stderr, returns a
non-zero code, and **leaves the previous WAV and the previous WebVTT exactly
where they were**. Run it over eleven films and the two that failed scroll
off the top while nine success lines print under them.

So on 2026-10-27 the text of every film was rewritten, twenty of the
twenty-two tracks were re-spoken, and `sprezzature.en` and `colors.en` kept a
voice recorded that morning — eight hours and two rewrites earlier. Nothing
said so. The films rendered, the page served them, and the only way to find
out was to notice two file timestamps among twenty-two.

What this checks
----------------
That each ``<film>.<lang>.vtt`` says what ``make_captions.FILMS`` says it
should. The WebVTT is written in the same breath as the WAV and only on
success, so a caption track that matches the script is a track whose audio
was spoken from that script. A stale WAV always drags a stale VTT with it,
which is what makes the cheap artefact a sound proxy for the expensive one.

Text only, not timings: the timings come out of a text-to-speech engine and
differ by milliseconds between machines, which is not a thing to gate on.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "brag-output"))

VIDEO = ROOT / "web" / "video"
ASSETS = ROOT / "brag-output" / "_assets"

#: A cue: an index line, a timing line, then the text until a blank line.
CUE = re.compile(r"^\d+\n[\d:.]+ --> [\d:.]+\n(.+?)(?=\n\n|\n*\Z)",
                 re.M | re.S)


def _spoken(vtt: Path) -> list[str]:
    """What a caption track says, one entry per cue, newlines flattened."""
    return [" ".join(m.group(1).split())
            for m in CUE.finditer(vtt.read_text(encoding="utf-8"))]


def _cuts() -> list[tuple[str, str]]:
    import make_captions

    return [(film, lang)
            for film, langs in make_captions.FILMS.items()
            for lang, lines in langs.items()
            if len(lines) >= 8]       # the retired eighteen-second group cuts


def test_the_caption_track_of_each_film_is_its_current_script() -> None:
    """Both languages, every film that is still cut."""
    import make_captions

    if not VIDEO.is_dir():
        pytest.skip("web/video is gitignored and absent from this clone")

    stale: list[str] = []
    for film, lang in _cuts():
        vtt = VIDEO / f"{film}.{lang}.vtt"
        if not vtt.is_file():
            stale.append(f"{film}.{lang}: no {vtt.name} at all")
            continue
        want = [" ".join(text.split())
                for _start, _dur, text in make_captions.FILMS[film][lang]]
        got = _spoken(vtt)
        if got == want:
            continue
        if len(got) != len(want):
            stale.append(
                f"{film}.{lang}: {len(want)} lines in the script, "
                f"{len(got)} cues on disk"
            )
            continue
        for n, (a, b) in enumerate(zip(want, got), 1):
            if a != b:
                stale.append(
                    f"{film}.{lang} line {n} was re-written and never "
                    f"re-spoken:\n      script: {a!r}\n      track:  {b!r}"
                )
    assert not stale, (
        f"{len(stale)} track(s) disagree with the script they came from. "
        f"`python3 brag-output/narrate_films.py <film> --lang <lang>` — and "
        f"read its exit code: it leaves the old track in place when a line "
        f"overruns its slot.\n  " + "\n  ".join(stale)
    )


def test_every_film_that_has_a_caption_track_has_the_voice_beside_it() -> None:
    """The WAV and the WebVTT are written together or not at all."""
    if not ASSETS.is_dir():
        pytest.skip("_assets is gitignored; run restore_assets.py --fix")

    missing = [
        f"{film}.{lang}: vo-{film}.{lang}.wav"
        for film, lang in _cuts()
        if (VIDEO / f"{film}.{lang}.vtt").is_file()
        and not (ASSETS / f"vo-{film}.{lang}.wav").is_file()
    ]
    assert not missing, "\n  ".join(["a caption track with no voice:", *missing])
