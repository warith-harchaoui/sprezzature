"""
The eleven films, read by the suite's own checker — in the voice, not the frame.

What was already checked, and what was not
------------------------------------------
``test_every_film_follows_the_kawasaki_pitch`` checks the *scene list*: every
scene declares its beat, and the beats never run backwards. That is the spine
of the picture, and nothing had ever read the spine of the *voice* over it.

A sixty-second film puts one sentence a scene on screen and speaks eight. Most
of what a viewer receives is the narration, and until this file nothing read
it at all.

What this catches, and what it cannot
--------------------------------------
Structure. A beat that is on screen and never spoken, beats spoken out of
order, a problem the voice does not reach in time, a magic beat that is a
label or an inventory. Each of those was sabotaged into the real films to
check it fires: silencing the ``colors`` problem beat, thinning the ``ui``
magic beat to "It just works.", rewriting it in brochure.

Not whether the insight is the *right* insight. Three films were wrong in
exactly that way and this guard clears all three, which is worth writing down
rather than hiding:

``audio``
    recited its five published numbers and closed on a callback instead of the
    sentence that makes them interesting — conventions rather than laws, which
    is why each one is a flag. Measured, the inventory is 12 of its 40 words,
    well under the share that makes a beat an inventory. Correctly cleared,
    and still the wrong beat.
``maps``
    spent its magic on the plate that draws no map and never said the
    mechanism: that ACLED and UCDP both record how well a coordinate is known,
    and that a tool drawing every one as the same dot asserts a street corner
    the source never gave. Well-formed prose about the wrong thing.
``sprezzature``
    named the vision model and stopped one clause short of the point, which is
    that what you then fix is the source.

All three were found by reading each film against its row in ``KAWASAKI.md``
with the package open beside it. That is a human job and ``pitch`` says so in
its own docstring. This file holds the half that can be decided, so the half
that cannot is the only one left to do by hand.

Why the spec is built here rather than written down
----------------------------------------------------
``sprezzature_video`` reads a ``FilmSpec``, and the obvious way to give it one
is a YAML file per film. That would be eleven copies of text that already
exists in ``build_films.FILMS`` and ``make_captions.FILMS``, and a copy of a
script is a script that goes stale — which is the exact failure the package
exists to catch, reproduced in the fixture meant to catch it.

So the spec is assembled from the generators themselves. ``films.yaml`` keeps
the ``claims``, because a claim's deciding file lives nowhere else; everything
here is derived.

How a narration line gets its beat
-----------------------------------
From the picture it lands on. The scene on screen when a line starts already
declares its beat, so there is one declaration rather than two, and a line
cannot be filed under a beat the frame behind it disagrees with.

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

pytest.importorskip(
    "sprezzature_video", reason="pip install sprezzature-video"
)

from sprezzature_video import calque, pitch  # noqa: E402
from sprezzature_video.captions import Spoken  # noqa: E402
from sprezzature_video.spec import FilmSpec  # noqa: E402

#: The beats `sprezzature_video.pitch` checks. `what` and `cta` are on the
#: suite's scene spine and are not Kawasaki's three, so a line landing on one
#: of them belongs to no checked beat — which is right: an opening wordmark is
#: not a problem statement.
CHECKED = pitch.BEATS


def _specs() -> dict[str, FilmSpec]:
    """One spec per minute-long film, built from the generators."""
    import build_films
    import make_captions

    out: dict[str, FilmSpec] = {}
    for film, spec in build_films.FILMS.items():
        if spec["duration"] < 30:
            continue  # the retired eighteen-second group cuts
        beats: dict[str, list[int]] = {}
        for index, scene in enumerate(spec["scenes"]):
            beat = scene.get("beat")
            if beat in CHECKED:
                beats.setdefault(beat, []).append(index)
        out[film] = FilmSpec(
            name=film,
            pitch=beats,
            scenes=[
                {"text": "", "start": float(scene["start"])}
                for scene in spec["scenes"]
            ],
            narration={
                lang: [
                    Spoken(start=start, text=text, duration=nominal)
                    for start, nominal, text in lines
                ]
                for lang, lines in make_captions.FILMS[film].items()
            },
        )
    return out


def test_the_films_this_reads_are_actually_there() -> None:
    """A guard over an empty set passes for the wrong reason."""
    specs = _specs()
    assert len(specs) >= 11, (
        f"only {len(specs)} minute-long film(s) assembled. Either the set "
        f"shrank or this file stopped finding it."
    )
    for film, spec in specs.items():
        assert set(spec.narration) == {"en", "fr"}, (
            f"{film} is not cut in both languages: {sorted(spec.narration)}"
        )


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_every_cut_delivers_the_three_beats_out_loud(lang: str) -> None:
    """Problem, solution, magic — spoken, in order, each with its shape."""
    findings: list[str] = []
    for film, spec in _specs().items():
        report = pitch.from_narration(spec, lang, 60.0)
        findings += [f"{film}.{lang}: {f}" for f in report.findings]
    assert not findings, (
        f"{len(findings)} finding(s) in the {lang} narration. The scene list "
        f"can be in Kawasaki's order while the voice over it is not — that is "
        f"what this reads.\n  " + "\n  ".join(findings)
    )


def test_the_problem_beat_is_spoken_and_not_only_shown() -> None:
    """The failure that needs naming on its own.

    A beat with no narration at all is reported by the check above as a
    missing beat, and its message reads as "this film has no problem" — which
    is wrong and sends a reader to the scene list. It has one on screen and
    says nothing about it, which is a different repair.
    """
    silent: list[str] = []
    for film, spec in _specs().items():
        for lang in ("en", "fr"):
            report = pitch.from_narration(spec, lang, 60.0)
            missing = [b for b in CHECKED if b not in report.beats]
            shown = [b for b in missing if spec.pitch.get(b)]
            silent += [f"{film}.{lang}: {b} is on screen and never spoken"
                       for b in shown]
    assert not silent, (
        f"{len(silent)} beat(s) are in the picture and absent from the voice:"
        f"\n  " + "\n  ".join(silent)
    )


def test_no_film_ships_a_french_cut_that_is_its_english_one_translated() -> None:
    """Two cuts, written. Not one cut and a rendering of it.

    The rule, and the state this repository was actually in: on screen the two
    languages are composed side by side and were fine; the narration table was
    English with French words, eleven times over, and nothing read it. Two of
    the rewritten cuts were still translations and this measure is what said
    so — at 0.91 and 0.80, where the eleven known-translated ones sat between
    0.75 and 0.89.
    """
    findings: list[str] = []
    for spec in _specs().values():
        findings += calque.compare_spec(spec).report()
    assert not findings, (
        f"{len(findings)} film(s) ship a French cut that reads as a rendering "
        f"of the English one. Two scripts written separately distribute their "
        f"material differently — a different number of lines, a clause split "
        f"here and run on there.\n  " + "\n  ".join(findings)
    )
