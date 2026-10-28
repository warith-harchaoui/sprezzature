"""
Every film says what it is, then the problem, the solution and the magic.

Guy KAWASAKI's order, adopted 2026-10-27 for the whole set. A viewer who does
not know the package needs the pain before the cure, and the cure before the
clever part. Lead with the mechanism and the first twenty seconds are spent on
a person who has not yet been told why they should care.

Why this is a test and not a comment
------------------------------------
It was a comment first. Seven of the eleven films carried a ``# PROBLEM`` /
``# SOLUTION`` / ``# SECRET SAUCE`` banner through their scene list and four
did not, and nothing said whether those four were exceptions or oversights —
the only way to find out was to read seventy scenes and judge each one. A
shared order that lives in comments is a shared order until the first person
adds a scene in a hurry.

So the order is declared. Each scene carries ``beat="problem"`` /
``"what"`` / ``"solution"`` / ``"magic"`` / ``"cta"``, and this file checks that the
beats of a film run down that list without going back up. A scene added in
the wrong place fails here, by name, before anything is rendered.

What is deliberately *not* checked
----------------------------------
How long each beat lasts, how many scenes it gets, or which scene types it
uses. ``colors`` spends fourteen seconds on the problem and twenty-two on one
picture; ``cli-gui`` is in the solution by the sixth second. That variety is
the point: a shared order is a way of being understood, a shared format is a
way of being skipped. The spine is checked, the execution is not.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "brag-output"))

#: The beats, in the only order they may appear in. A film skips a beat at
#: its peril but may not reverse one.
SPINE = ("what", "problem", "solution", "magic", "cta")


def _films() -> dict[str, dict]:
    """The minute-long films, which are the ones that carry a spine.

    The eighteen-second group cuts predate one-film-per-brick. They are kept
    only until the copies on the server are deleted by hand, and giving them
    a spine would be writing a pitch for a film nobody will watch again.
    """
    import build_films

    return {k: v for k, v in build_films.FILMS.items() if v["duration"] >= 30}


def test_every_scene_declares_which_beat_it_belongs_to() -> None:
    """No scene is left to be classified by whoever reads it next."""
    missing = [
        f"{film} scene {i} ({scene['type']}, {scene['start']}s)"
        for film, spec in _films().items()
        for i, scene in enumerate(spec["scenes"])
        if scene.get("beat") not in SPINE
    ]
    assert not missing, (
        f"{len(missing)} scene(s) carry no beat, or one that is not "
        f"{SPINE}:\n  " + "\n  ".join(missing)
    )


def test_the_beats_of_a_film_never_run_backwards() -> None:
    """problem → solution → sauce → close, and never the other way.

    The failure this catches is not someone writing a film upside down. It is
    a scene inserted where there was room on the beat grid rather than where
    it belongs in the argument — a second problem statement dropped in after
    the solution, which reads to a viewer as the film changing its mind.
    """
    wrong: list[str] = []
    for film, spec in _films().items():
        rank = -1
        for i, scene in enumerate(spec["scenes"]):
            got = SPINE.index(scene["beat"])
            if got < rank:
                wrong.append(
                    f"{film} scene {i} ({scene['type']}, {scene['start']}s) is "
                    f"{scene['beat']!r} after {SPINE[rank]!r}"
                )
            rank = max(rank, got)
    assert not wrong, (
        "the spine runs backwards in "
        f"{len(wrong)} place(s):\n  " + "\n  ".join(wrong)
    )


def test_every_film_opens_on_the_problem_and_lands_the_sauce() -> None:
    """The three beats a pitch cannot do without are all present.

    ``what`` is the identity card, complete on frame zero: the package's
    name, one line saying what it is, and where to find it. ``cta`` is the
    closing ask. Neither is part of the argument, and both bracket it. What
    a film may not do is open on its solution, which is
    the shape every one of these had before the rewrite: a package
    introducing itself to somebody who never said they had the problem.
    """
    bad: list[str] = []
    for film, spec in _films().items():
        beats = [s["beat"] for s in spec["scenes"]]
        if beats[0] != "what":
            bad.append(f"{film} opens on {beats[0]!r}, not on the identity card")
        for want in ("problem", "solution", "magic"):
            if want not in beats:
                bad.append(f"{film} never reaches the {want}")
    assert not bad, "\n  ".join(["", *bad])


def test_every_film_closes_on_an_ask_and_names_its_own_repository() -> None:
    """The last slide is Kawasaki's, and it asks for something.

    The films closed on "Make it. Audit it. Then look at it." until
    2026-10-28 — a motto, which is a thing to admire rather than a thing to
    do. A viewer who liked the minute had nowhere to put that.

    Two asks now, and the star points at the package the film is about. The
    failure this guards is the lazy one: pointing all eleven at the monorepo
    because that is what the constant already said. Somebody who has just
    watched a minute on ``maps`` wants ``sprezzature-maps``; sending them to
    the hub is a redirect dressed up as a destination.
    """
    import build_films

    bad: list[str] = []
    for film, spec in _films().items():
        close = spec["scenes"][-1]
        if close["type"] != "cta":
            bad.append(f"{film} ends on a {close['type']!r} scene, not an ask")
            continue
        wheres = [where for _glyph, _doing, where in close["actions"]]
        repo = "sprezzature" if film == "sprezzature" else f"sprezzature-{film}"
        want = f"{build_films.GITHUB}/{repo}"
        if want not in wheres:
            bad.append(f"{film} does not send anyone to {want}: {wheres}")
        if "sprezzature.ai" not in wheres:
            bad.append(f"{film} never names the site: {wheres}")
    assert not bad, "\n  ".join(["", *bad])


def test_every_film_opens_on_the_same_sentence() -> None:
    """"Sprezzature is an AI engine for Design", in all eleven, both languages.

    A viewer arrives at one film, not at the set. Whichever one they land on
    has to say what the whole thing is before it says which part of it they
    are watching — otherwise the eleven films are eleven products.

    Checked on screen *and* in the voice, because the two are written in
    different files and either can lose it alone: the card is a scene in
    ``build_films.FILMS``, the spoken line is the first entry in
    ``make_captions.FILMS``.
    """
    import build_films
    import make_captions

    missing: list[str] = []
    for film, lang in build_films.cuts():
        spec = build_films.FILMS[film]
        if spec["duration"] < 30:
            continue
        want = build_films.say(build_films.TAGLINE, lang)

        card = spec["scenes"][0]
        on_screen = build_films.say(card.get("tagline", ""), lang)
        if on_screen != want:
            missing.append(f"{film}.{lang}: the card says {on_screen!r}")

        spoken = make_captions.FILMS[film][lang][0][2]
        if not spoken.startswith(want):
            missing.append(
                f"{film}.{lang}: the first spoken line does not open on it "
                f"({spoken[:60]!r}…)"
            )
    assert not missing, "\n  ".join(["", *missing])


def test_the_closing_ask_is_also_spoken() -> None:
    """The two asks are said out loud, not only printed.

    The card above is checked in ``build_films``; the voice lives in
    ``make_captions`` and can lose the ask on its own. A viewer watching on a
    phone, held low, hears the minute more reliably than they read its last
    four seconds, so the close has to survive in either channel alone.

    Only the two nouns are checked. How the sentence is built is the
    writer's: English asks in two clauses, French in two sentences.
    """
    import build_films
    import make_captions

    silent: list[str] = []
    for film, lang in build_films.cuts():
        if build_films.FILMS[film]["duration"] < 30:
            continue
        spoken = make_captions.FILMS[film][lang][-1][2]
        for noun in ("GitHub", "sprezzature.ai"):
            if noun not in spoken:
                silent.append(f"{film}.{lang}: the last line never says {noun!r} ({spoken!r})")
    assert not silent, "\n  ".join(["", *silent])
