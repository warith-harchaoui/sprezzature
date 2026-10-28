"""
A track that says the right words, in a voice the suite no longer chooses.

``test_no_film_is_voiced_by_a_stale_track`` compares the cues with the script
and catches the obvious half: a line rewritten and never re-spoken. It is
blind to the other half, and the other half happened.

On 2026-10-28 `speaker-helper` 0.12 made offline French the owner's ratified
choice of chatterbox, and 0.13 sent offline narration to chatterbox in every
language. Five French tracks went on passing the freshness guard word for
word while kokoro's voice was still in them. Nothing in a WAV or a WebVTT says
who read it, so nothing could notice — and a mixed set is the kind of defect
that survives every diff and is obvious in the second film somebody watches.

So ``narrate_films.py`` writes what spoke, beside what was spoken, and this
reads it back. The stamp sits next to the cues rather than next to the audio
because ``_assets/`` is the tree ``restore_assets.py`` counts and the ``video``
film puts that count on screen.

Why the router and not a constant
---------------------------------
The expected engine is asked of `speaker-helper` through
``narrate_films.voice_of``, the same call the narrator makes. A constant here
would be a third opinion about the suite's own voice, and this file exists
because second opinions drift.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BRAG = REPO_ROOT / "brag-output"
VIDEO = REPO_ROOT / "web" / "video"

sys.path.insert(0, str(BRAG))


def _cuts() -> list[tuple[str, str]]:
    import build_films

    return [
        (film, lang)
        for film, lang in build_films.cuts()
        if build_films.FILMS[film]["duration"] >= 30
    ]


def test_every_track_was_spoken_by_the_engine_the_router_names() -> None:
    """Both languages, every film that is still cut."""
    if not VIDEO.is_dir():
        pytest.skip("web/video is gitignored and absent from this clone")
    pytest.importorskip("speaker_helper", reason="pip install speaker-helper")

    import narrate_films

    wrong: list[str] = []
    for film, lang in _cuts():
        stamp = VIDEO / f"{film}.{lang}.voice.json"
        if not stamp.is_file():
            wrong.append(
                f"{film}.{lang}: no {stamp.name}, so nothing says which voice "
                f"read it. Re-narrate it."
            )
            continue
        said = json.loads(stamp.read_text(encoding="utf-8"))
        engine, voice = narrate_films.voice_of(lang)
        if said.get("engine") != engine:
            wrong.append(
                f"{film}.{lang}: spoken by {said.get('engine')!r}; the router "
                f"now names {engine!r}"
            )
        elif said.get("voice") != voice:
            wrong.append(
                f"{film}.{lang}: spoken with voice {said.get('voice')!r}; "
                f"{engine} now reads {lang} with {voice!r}"
            )
    assert not wrong, (
        f"{len(wrong)} track(s) carry a voice this suite no longer chooses. "
        f"`python3 brag-output/narrate_films.py <film> --lang <lang>`\n  "
        + "\n  ".join(wrong)
    )
