"""
The films are checked by the package that exists to check films.

``sprezzature-video`` ships ``pitch``, which reads Guy KAWASAKI's three beats
out of a film and reports what they get wrong. It was written against this
suite's own first set, and the three failures in its docstring are three
failures those films actually had. Running the eleven current films through
it is the suite auditing itself, which is the thing the suite is for.

Why this and `test_every_film_follows_the_kawasaki_pitch` both exist
--------------------------------------------------------------------
They ask different questions and neither subsumes the other.

The sibling test checks **structure**: every scene declares a beat, the beats
never run backwards, each film opens on the problem and reaches the magic.
It is cheap, it runs on the spec, and it fails by naming the scene.

This one checks **shape**, and only the package knows those rules: a magic
beat under six words is a label rather than an insight; a magic beat matching
the feature-list pattern is an inventory of what ships; a problem arriving
after 22% of the running time leaves the viewer watching a solution to
nothing. Those thresholds live in `sprezzature_video.pitch` and belong
there — re-deriving them here would be a second copy to go stale.

The beats come from the ``beat=`` key on each scene rather than from a
separate ``pitch:`` block of scene indices. Indices are what the package's
own `from_spec` takes, and they are the version that drifts: insert a scene
and every index after it is quietly wrong, with nothing to say so.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "brag-output"))

#: Scene keys that put words on screen. ``mark`` is the wordmark on the
#: closing card and is the package's name, not an argument.
TEXT_KEYS = ("line", "caption", "eyebrow", "items", "rows", "steps", "code")


def _text_of(scene: dict) -> str:
    """Every word one scene shows, flattened."""
    out: list[str] = []
    for key in TEXT_KEYS:
        value = scene.get(key)
        if isinstance(value, str):
            out.append(value)
        elif isinstance(value, (list, tuple)):
            out += [v for v in value if isinstance(v, str)]
    for claim in scene.get("claims", ()):
        if isinstance(claim, (list, tuple)) and isinstance(claim[0], str):
            out.append(claim[0])
    return " ".join(out)


def _beats(spec: dict, pitch) -> dict:
    """One :class:`Beat` per Kawasaki beat, built off the scenes' own keys."""
    beats: dict = {}
    for name in pitch.BEATS:
        scenes = [(i, sc) for i, sc in enumerate(spec["scenes"])
                  if sc.get("beat") == name]
        if not scenes:
            continue
        beats[name] = pitch.Beat(
            name=name,
            scenes=tuple(i for i, _ in scenes),
            text=" ".join(_text_of(sc) for _, sc in scenes),
            start=min(sc["start"] for _, sc in scenes),
            source="build_films.FILMS",
        )
    return beats


def test_every_cut_passes_sprezzature_video_pitch() -> None:
    """Eleven films, both languages, through the suite's own checker.

    Both languages because the thresholds are counted in words and French
    runs longer than English for the same sentence — a magic beat can clear
    six words in one language and not the other.
    """
    pitch = pytest.importorskip(
        "sprezzature_video.pitch",
        reason="pip install sprezzature-video",
    )
    import build_films

    findings: list[str] = []
    for film, lang in build_films.cuts():
        spec = build_films.FILMS[film]
        if spec["duration"] < 30:
            continue        # the retired eighteen-second group cuts
        localised = build_films.in_language(spec, lang, film)
        report = pitch.check(
            f"{film}.{lang}", _beats(localised, pitch), spec["duration"]
        )
        findings += report.findings

    assert not findings, (
        f"{len(findings)} pitch finding(s) from sprezzature-video:\n  "
        + "\n  ".join(findings)
    )
