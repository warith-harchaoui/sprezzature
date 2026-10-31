"""
A counted quantity in a film is written in digits, never spelled out.

Why digits
----------
Owner's rule, 2026-10-29, for every film in the series. A number is the part
of a sentence a viewer is meant to *take away*, and a digit is read in one
fixation where a word has to be parsed. "17 characters a second. 42 to a
line." lands; "Seventeen characters a second. Forty-two to a line." reads like
prose about numbers.

It also removes a place for a correction to get dropped. Before this rule the
`figures` count lived as a digit on the card and as a word in two narration
lines, and a guard existed solely to compare the three. The card moved once
and the words did not.

What this refuses, and what it must not
---------------------------------------
Only **cardinal quantities**: a count of things. Not the article `un` / `une`
/ `a`, not `one` standing in for a noun ("the one nobody declared"), not
`deux` in `les deux sens`, and not an ordinal. Those are grammar, and turning
them into digits would be vandalism, so the pattern below requires the number
word to be followed by something being counted.

The list is deliberately short. It holds the words that actually appeared in
the eleven films when the rule was written, plus the rest of the small
cardinals, and it is a keyword check rather than a parser: a guard that tries
to understand French grammar would be wrong in a way nobody could debug.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "brag-output"))

#: Number words, by language. `one`, `un` and `une` are absent on purpose:
#: they are articles far more often than counts, and no rule a test can state
#: separates the two reliably.
WORDS = {
    "en": (
        "two three four five six seven eight nine ten eleven twelve thirteen "
        "fourteen fifteen sixteen seventeen eighteen nineteen twenty thirty "
        "forty fifty sixty seventy eighty ninety hundred"
    ).split(),
    "fr": (
        "deux trois quatre cinq six sept huit neuf dix onze douze treize "
        "quatorze quinze seize dix-sept dix-huit dix-neuf vingt trente "
        "quarante cinquante soixante cent cents"
    ).split(),
}

#: What makes a number word a *count*: something plural right after it. This
#: is what keeps `les deux sens` out (`sens` is not matched as plural here)
#: while catching `deux menus`, and it is why the check is a suspicion rather
#: than a proof. A false positive is rewritten in a second; a false negative
#: costs a render.
COUNTED = re.compile(
    r"(?P<lead>\b[A-Za-zÀ-ÿ']+\s+)?"
    r"\b(?P<number>" + "|".join(WORDS["en"] + WORDS["fr"]) + r")[\s-]+"
    r"(?P<thing>[A-Za-zÀ-ÿ]+s)\b",
    re.IGNORECASE,
)

#: A definite article in front of a number word makes it "both", not a count.
#: `les deux listes` and `the two lists` name a pair already introduced; they
#: are grammar, and "the 2 lists" is not English.
#:
#: Found by the guard itself on its first run, which reported nine lines that
#: were all correct. A guard whose first answer is nine false positives is
#: measuring the wrong thing, and the cheapest moment to notice is before
#: anybody edits a film to satisfy it.
BOTH = frozenset("les des the ces aux both".split())

#: Plural-looking words that are not things being counted, so a number in
#: front of them is not a count. `sens` and `fois` are invariable in French;
#: the rest are ordinary words that happen to end in `s`.
NOT_A_THING = frozenset(
    "sens fois pas plus moins mois temps corps cours puis sous dans sans "
    "is as was has this his its us".split()
)


#: Cardinals that cannot be anything but a number, in either language. A
#: count does not stop being a count because the noun it counts sits in the
#: label beside it: the `publish` film's indexes stage read "six, for
#: crawlers", where the thing counted is the stage's own name. `COUNTED`
#: requires a plural right after the number and so reported nothing.
#:
#: What makes this safe is the list, not the pattern. Every word here is a
#: number and nothing else, so a bare occurrence needs no grammar to judge.
#: The ambiguous ones are left out by name and each for its own reason:
#: `one` / `un` / `une` are articles, `two` / `deux` carry the "both"
#: pronoun, `neuf` is also "new", and `cent` is also "pour cent". Run across
#: all 801 strings the films render and speak, this reports exactly the two
#: it was built for and nothing else.
SOLO_CARDINALS: tuple[str, ...] = (
    "three four five six seven eight nine ten eleven twelve thirteen "
    "fourteen fifteen sixteen seventeen eighteen nineteen twenty thirty "
    "forty fifty sixty seventy eighty ninety "
    "trois quatre cinq sept huit dix onze douze treize quatorze quinze "
    "seize vingt trente quarante cinquante soixante"
).split()

SOLO = re.compile(r"\b(?P<number>" + "|".join(SOLO_CARDINALS) + r")\b", re.IGNORECASE)


def _spelled_solo(text: str) -> list[str]:
    """Unambiguous number words in *text*, counted noun or not."""
    return [m.group("number") for m in SOLO.finditer(text)]


def _lines() -> list[tuple[str, str, int, str]]:
    """Every narration line: film, language, position, text."""
    import make_captions

    return [
        (film, lang, n, text)
        for film, langs in make_captions.FILMS.items()
        for lang, rows in langs.items()
        for n, (_start, _dur, text) in enumerate(rows, 1)
    ]


#: Scene keys holding one string, or one `L()` pair of them.
PLAIN_KEYS: tuple[str, ...] = ("line", "caption", "eyebrow", "mark", "tagline")

#: Scene keys holding a *sequence* of strings, or of tuples of them: the
#: labels on a flow's stages, a list's items, a table's rows, a sequence's
#: steps.
#:
#: These were not read until 2026-10-30, and the gap was not theoretical. The
#: `publish` film's icons stage said "one logo, eleven files" and its indexes
#: stage said "six, for crawlers" -- both spelled out, both directly under an
#: eyebrow reading "7 of the 10 tools" in digits. The scene disagreed with
#: itself on screen and this file reported no finding, because it never
#: looked at that half of the scene.
#:
#: The lesson is the shape rather than the two strings: a guard that reads
#: some of the fields a film renders will pass a film that fails the rule,
#: and it will do it silently, which is worse than not existing.
SEQUENCE_KEYS: tuple[str, ...] = ("items", "rows", "steps", "stages")


def _strings(value: object) -> list[str]:
    """Every display string inside *value*, however it is nested.

    A scene holds plain strings, `L()` pairs, tuples of either, and lists of
    those tuples. Walking the shape rather than enumerating it means a new
    kind of scene is read the day it is written, not the day somebody
    remembers to extend this.
    """
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [str(v) for v in value.values() if isinstance(v, str)]
    if isinstance(value, (list, tuple)):
        return [s for item in value for s in _strings(item)]
    return []


def _screen() -> list[tuple[str, int, str]]:
    """Every string a film puts on screen: film, scene index, text."""
    import build_films

    out: list[tuple[str, int, str]] = []
    for film, spec in build_films.FILMS.items():
        for i, scene in enumerate(spec["scenes"]):
            for key in PLAIN_KEYS + SEQUENCE_KEYS:
                out += [(film, i, text) for text in _strings(scene.get(key))]
    return out


def _spelled_counts(text: str) -> list[str]:
    """Number words in *text* that look like counts of something."""
    return [
        f"{m.group('number')} {m.group('thing')}"
        for m in COUNTED.finditer(text)
        if m.group("thing").lower() not in NOT_A_THING
        and (m.group("lead") or "").strip().lower() not in BOTH
    ]


def test_there_is_something_to_check() -> None:
    """A precondition that cannot quietly become false."""
    assert len(_lines()) >= 150, f"only {len(_lines())} narration lines found"
    assert len(_screen()) >= 50, f"only {len(_screen())} on-screen strings found"


def test_no_spoken_line_spells_a_count() -> None:
    """The narration says 17, not seventeen."""
    bad = [
        f"{film}.{lang} line {n}: {hits} — {text!r}"
        for film, lang, n, text in _lines()
        if (hits := _spelled_counts(text))
    ]
    assert not bad, (
        f"{len(bad)} narration line(s) spell a count instead of writing the "
        f"digits:\n  " + "\n  ".join(bad)
    )


def test_no_frame_spells_a_count() -> None:
    """Neither does anything printed on screen."""
    bad = [
        f"{film} scene {i}: {hits} — {text!r}"
        for film, i, text in _screen()
        if (hits := _spelled_counts(text))
    ]
    assert not bad, (
        f"{len(bad)} on-screen string(s) spell a count instead of writing the "
        f"digits:\n  " + "\n  ".join(bad)
    )


def test_no_screen_string_spells_a_bare_cardinal() -> None:
    """A count whose noun sits in the label beside it is still a count."""
    bad = [
        f"{film} scene {i}: {hits} — {text!r}"
        for film, i, text in _screen()
        if (hits := _spelled_solo(text))
    ]
    assert not bad, (
        f"{len(bad)} on-screen string(s) spell a number that can only be a "
        "number:\n  " + "\n  ".join(bad)
    )


def test_no_spoken_line_spells_a_bare_cardinal() -> None:
    """The same rule, in the half of the film a viewer mostly receives."""
    bad = [
        f"{film}.{lang} line {n}: {hits} — {text!r}"
        for film, lang, n, text in _lines()
        if (hits := _spelled_solo(text))
    ]
    assert not bad, (
        f"{len(bad)} narration line(s) spell a number that can only be a "
        "number:\n  " + "\n  ".join(bad)
    )
