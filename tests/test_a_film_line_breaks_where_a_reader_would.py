"""
No film line breaks between words a reader keeps together.

``text-wrap: balance`` equalises line *lengths*. It knows nothing about what
the words mean, so it will happily put ``30`` at the end of one line and
``laws`` at the start of the next, leave ``de`` hanging in a French cut, or
part ``WCAG`` from ``1.4.2``. Measured on 2026-11-01 across all eleven films,
both languages and all three canvases: **76** such breaks were available — 63
short words that could be left at a line end, 11 numbers that could be parted
from their noun, 2 names from their number.

Why the fix is in the text and not in the stylesheet
----------------------------------------------------
A no-break space is the only instruction that survives every wrapping
algorithm. ``balance``, ``pretty`` and greedy all honour U+00A0; none of them
can be told *which* break is semantically wrong. So
``build_films.bind`` puts the space in, and the stylesheet keeps deciding how
the remaining breaks are distributed. The two are not alternatives, and this
file asserts both halves.

The second half is the one that bites
-------------------------------------
Binding costs break opportunities, and a binding that is too eager is worse
than the break it avoided. The first version chained short words: ``que pas de
surlignage`` became one unbreakable block **96 %** of the portrait column
wide, which leaves that line no options at all. Capping short-word groups at
two words brought the worst case to 83 %, and that one — ``une
demi-seconde.`` in a hero line — is a pair worth binding.

So the ceiling is asserted here, with the real font at the real column width,
because the generator has no font metrics and should not grow any: it emits
text, and whether that text fits is a measurement.

Author
------
Project maintainers.
"""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "brag-output"))

FONT = ROOT / "web/fonts/roboto/Roboto-Variable.woff2"
NBSP = " "

#: A bound group may fill this share of its column and no more. Above it the
#: line has no room to be balanced, which is the failure binding was meant to
#: prevent. The measured worst case is 0.83.
GROUP_SHARE = 0.90

#: Which font size each prose place is set at, per canvas key in FORMATS.
PLACES = {"caption": "body", "line": "hero"}


@lru_cache(maxsize=2)
def _advances() -> tuple[dict[int, int], int]:
    from fontTools.ttLib import TTFont

    font = TTFont(FONT)
    hmtx, cmap = font["hmtx"], font.getBestCmap()
    return ({cp: hmtx[g][0] for cp, g in cmap.items() if g in hmtx.metrics},
            font["head"].unitsPerEm)


def _width(text: str, size: float) -> float:
    table, upem = _advances()
    fallback = table.get(ord("?"), upem // 2)
    return sum(table.get(ord(c), fallback) for c in text) / upem * size


def _prose() -> list[tuple[str, str, str, str]]:
    """Every on-screen prose string: (format, film.lang, place, text)."""
    import build_films

    out = []
    for fmt in build_films.FORMATS:
        for film, lang in build_films.cuts():
            spec = build_films.FILMS[film]
            if spec["duration"] < 30:
                continue
            spec = build_films.in_language(spec, lang, film)
            for index, scene in enumerate(spec["scenes"]):
                for place in PLACES:
                    text = scene.get(place)
                    if isinstance(text, str) and text.strip():
                        out.append((fmt, f"{film}.{lang} s{index}", place, text))
    return out


def test_the_font_and_the_films_are_both_here() -> None:
    """Without either there is no measurement, only a green tick."""
    pytest.importorskip("fontTools", reason="fontTools reads the advance widths")
    assert FONT.is_file(), f"{FONT.relative_to(ROOT)} is missing"
    assert len(_prose()) > 100, f"only {len(_prose())} prose strings found"


def test_a_number_is_never_parted_from_its_word() -> None:
    """``30 laws``, ``20 accessibility``, ``4 workers``."""
    pytest.importorskip("fontTools")
    import build_films

    loose = []
    for fmt, where, place, text in _prose():
        bound = build_films.bind(" ".join(text.split()))
        words = bound.split(" ")
        for i in range(len(words) - 1):
            tail = words[i].split(NBSP)[-1]
            head = words[i + 1].split(NBSP)[0]
            if build_films._NUMBER.match(tail) and not build_films._NUMBER.match(head):
                if not tail.endswith((".", "!", "?", ":", ";")):
                    loose.append(f"{fmt} {where} {place}: {tail!r} / {head!r}")
    assert not loose, "a number can still fall at a line end:\n  " + "\n  ".join(loose)


def test_a_short_word_at_a_line_end_is_there_because_of_the_cap() -> None:
    """The 63-case majority, and the honest form of the promise.

    The first version of this test demanded that *no* short word can fall at a
    line end. ``bind`` cannot deliver that, and should not: capping chains at
    two words is what keeps a group from filling the column, so
    ``que pas de surlignage`` becomes ``que·pas de·surlignage`` and ``pas`` is
    left able to end a line.

    What is actually promised, and what this asserts, is that every such case
    is the *cap* rather than an oversight: a short word able to end a line must
    itself be the tail of a bound pair. A short word with a breakable space on
    both sides is a miss.
    """
    pytest.importorskip("fontTools")
    import build_films

    missed = []
    for fmt, where, place, text in _prose():
        bound = build_films.bind(" ".join(text.split()))
        groups = bound.split(" ")
        for i in range(len(groups) - 1):          # the last group ends the text
            tail = groups[i].split(NBSP)[-1]
            bare = tail.strip("«»\"'(),;:.!?").lower()
            if bare not in build_films.NO_LINE_END or len(bare) > 4:
                continue
            if tail.endswith((".", "!", "?", ":", ";")):
                continue                           # a sentence may end there
            if NBSP in groups[i]:
                continue                           # the cap: it is a pair's tail
            missed.append(f"{fmt} {where} {place}: {tail!r} in {groups[i]!r}")
    assert not missed, (
        "these short words can end a line and are not the tail of a bound "
        "pair, so nothing was holding them:\n  " + "\n  ".join(missed)
    )


def test_binding_removes_most_of_the_measured_cases() -> None:
    """The number that justified the work, kept honest.

    76 breaks were available before binding. If a later edit made ``bind`` a
    no-op the tests above would still pass on their own terms, so this one
    counts: the breakable short-word and number positions must be a small
    fraction of what they were.
    """
    pytest.importorskip("fontTools")
    import build_films

    def loose(text: str, use_bind: bool) -> int:
        words = (build_films.bind(text) if use_bind else text).split(" ")
        n = 0
        for i in range(len(words) - 1):
            tail = words[i].split(NBSP)[-1]
            bare = tail.strip("«»\"'(),;:.!?").lower()
            if tail.endswith((".", "!", "?", ":", ";")):
                continue
            if bare in build_films.NO_LINE_END and len(bare) <= 4:
                n += 1
            elif build_films._NUMBER.match(tail):
                n += 1
        return n

    before = sum(loose(" ".join(t.split()), False) for _, _, _, t in _prose())
    after = sum(loose(" ".join(t.split()), True) for _, _, _, t in _prose())
    assert before > 200, f"only {before} positions before binding; the walk is wrong"
    assert after < before * 0.45, (
        f"binding left {after} breakable positions out of {before}; it is barely doing anything"
    )


def test_a_sentence_boundary_stays_breakable() -> None:
    """The counterweight, and a bug this caught.

    ``fixed in 2009. Full deficiency`` is two sentences. Binding ``2009.`` to
    ``Full`` forbids a break at the one place a break is ideal. The first
    version of ``bind`` did exactly that, because it excused numbers from the
    sentence-end rule so that ``1.4.2`` would not read as one — an excuse that
    was never needed, since a version number does not end in a dot.
    """
    import build_films

    assert build_films.bind("fixed in 2009. Full deficiency").count(NBSP) == 1
    assert "2009." + NBSP not in build_films.bind("fixed in 2009. Full deficiency")
    assert build_films.bind("WCAG 1.4.2 fails") == f"WCAG{NBSP}1.4.2{NBSP}fails"


def test_no_bound_group_crowds_out_its_own_line() -> None:
    """Binding must not cost more than the break it buys.

    Chained short words did: ``que pas de surlignage`` filled 96 % of the
    portrait column as one unbreakable block. Capped at two words, the worst
    case is 83 %.
    """
    pytest.importorskip("fontTools")
    import build_films

    fat = []
    for fmt, where, place, text in _prose():
        f = build_films.FORMATS[fmt]
        column = f["w"] - 2 * f["pad"]
        size = f[PLACES[place]]
        for group in build_films.bind(" ".join(text.split())).split(" "):
            if NBSP not in group:
                continue  # one word is as narrow as the text allows
            share = _width(group.replace(NBSP, " "), size) / column
            if share > GROUP_SHARE:
                fat.append(f"{fmt} {where} {place}: {share:.0%} {group!r}")
    assert not fat, (
        f"these bound groups fill more than {GROUP_SHARE:.0%} of their column, "
        "so the line cannot be balanced:\n  " + "\n  ".join(fat)
    )


def test_short_words_do_not_chain() -> None:
    """Three in a row would merge into one block. Measured, then capped."""
    import build_films

    bound = build_films.bind("que pas de surlignage")
    assert bound == f"que{NBSP}pas de{NBSP}surlignage", bound
    assert NBSP + "de" + NBSP not in bound
