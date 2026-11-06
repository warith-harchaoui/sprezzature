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
``scripts/semantic_breaks.py`` puts the space in, and the stylesheet keeps deciding how
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

import re
import sys
from functools import lru_cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "brag-output"))
sys.path.insert(0, str(ROOT / "scripts"))

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
    import semantic_breaks as sb

    loose = []
    for fmt, where, place, text in _prose():
        words = sb.bind(text).split(" ")
        for i in range(len(words) - 1):
            tail = words[i].split(NBSP)[-1]
            head = words[i + 1].split(NBSP)[0]
            if sb._NUMBER.match(tail) and sb._kind(head) == "content" and not sb._NUMBER.match(head):
                if not tail.endswith((".", "!", "?", ":", ";", ",")):
                    loose.append(f"{fmt} {where} {place}: {tail!r} / {head!r}")
    assert not loose, "a number can still fall at a line end:\n  " + "\n  ".join(loose)


def test_no_function_word_can_end_a_line() -> None:
    """The 63-case majority, now kept without exception.

    The first ``bind`` capped chains at two words, so ``que pas de
    surlignage`` left ``pas`` free to end a line and a test had to excuse it
    as "the cap". The cap is gone because its reason is gone: a bound group
    no longer has to fit a line on its own, the phrase span around it wraps
    first. So the promise is the plain one: an article, a preposition, a
    conjunction never ends a line, unless it ends a sentence, or another
    function word follows it: ``de·chaque·coordonnée.`` bound end to end filled
    102 % of the portrait column, so that one gap stays as the last resort.
    """
    import semantic_breaks as sb

    missed = []
    for fmt, where, place, text in _prose():
        groups = sb.bind(text).split(" ")
        for i in range(len(groups) - 1):          # the last group ends the text
            tail = groups[i].split(NBSP)[-1]
            bare = sb._bare(tail)
            if bare not in sb.OPENERS and bare not in sb.LINKS:
                continue
            if tail.endswith((".", "!", "?", ":", ";", ",")):
                continue                           # a sentence may end there
            if sb._kind(groups[i + 1].split(NBSP)[0]) != "content":
                continue                           # the last resort: ``de chaque``
            missed.append(f"{fmt} {where} {place}: {tail!r} in {groups[i]!r}")
    assert not missed, "these function words can end a line:\n  " + "\n  ".join(missed)


def test_binding_removes_most_of_the_measured_cases() -> None:
    """The number that justified the work, kept honest.

    If a later edit made the module a no-op, the tests above would pass on an
    empty walk; this one counts the breakable function-word and number
    positions before and after.
    """
    import semantic_breaks as sb

    def loose(text: str) -> int:
        words = text.split(" ")
        n = 0
        for i in range(len(words) - 1):
            tail = words[i].split(NBSP)[-1]
            if tail.endswith((".", "!", "?", ":", ";", ",")):
                continue
            if sb._NUMBER.match(tail):
                n += 1
            elif sb._bare(tail) in sb.OPENERS | sb.LINKS:
                # ``de chaque``: the last-resort gap, priced, not loose.
                n += sb._kind(words[i + 1].split(NBSP)[0]) == "content"
        return n

    before = sum(loose(" ".join(t.split())) for _, _, _, t in _prose())
    after = sum(loose(sb.bind(t)) for _, _, _, t in _prose())
    assert before > 200, f"only {before} positions before binding; the walk is wrong"
    assert after < before * 0.1, f"binding left {after} breakable positions out of {before}"


def test_a_sentence_boundary_stays_breakable() -> None:
    """The counterweight, and a bug this caught.

    ``fixed in 2009. Full deficiency`` is two sentences. Binding ``2009.`` to
    ``Full`` forbids a break at the one place a break is ideal. The first
    version of ``bind`` did exactly that, because it excused numbers from the
    sentence-end rule so that ``1.4.2`` would not read as one — an excuse that
    was never needed, since a version number does not end in a dot.
    """
    import semantic_breaks as sb

    assert "2009." + NBSP not in sb.bind("fixed in 2009. Full deficiency")
    assert sb.bind("WCAG 1.4.2 fails") == f"WCAG{NBSP}1.4.2{NBSP}fails"


def test_no_bound_group_crowds_out_its_own_line() -> None:
    """Binding must not cost more than the break it buys.

    Chained short words did: ``que pas de surlignage`` filled 96 % of the
    portrait column as one unbreakable block. Capped at two words, the worst
    case is 83 %. The cap is gone and the guard stays: a function-word chain
    now keeps its last-resort gap, and ``de chaque coordonnée.`` (102 % bound
    end to end) is the case that put it there.
    """
    pytest.importorskip("fontTools")
    import build_films
    import semantic_breaks as sb

    fat = []
    for fmt, where, place, text in _prose():
        f = build_films.FORMATS[fmt]
        column = f["w"] - 2 * f["pad"]
        size = f[PLACES[place]]
        for group in sb.bind(text).split(" "):
            if NBSP not in group:
                continue  # one word is as narrow as the text allows
            share = _width(group.replace(NBSP, " "), size) / column
            if share > GROUP_SHARE:
                fat.append(f"{fmt} {where} {place}: {share:.0%} {group!r}")
    assert not fat, (
        f"these bound groups fill more than {GROUP_SHARE:.0%} of their column, "
        "so the line cannot be balanced:\n  " + "\n  ".join(fat)
    )


def test_the_seams_are_where_the_meaning_is() -> None:
    """The cases that started it, measured in the rendered films on 2026-11-06.

    Balance alone wrote ``Sprezzature est un moteur ⏎ d'IA pour le design``
    and ``It points at the ⏎ wrong line``; and ``n'y ⏎ a pas``, once the
    French verb ``a`` was read as the English article.
    """
    import semantic_breaks as sb

    def seams(text: str) -> list[str]:
        return [p.replace(NBSP, " ") for p in sb.phrases(text)]

    assert seams("Sprezzature is an AI engine for Design") == [
        "Sprezzature is", "an AI engine", "for Design"]
    assert seams("Sprezzature est un moteur d'IA pour le design") == [
        "Sprezzature est", "un moteur d'IA", "pour le design"]
    assert seams("It points at the wrong line, with confidence.") == [
        "It points", "at the wrong line,", "with confidence."]
    assert "n'y" + NBSP + "a" in sb.bind("Il n'y a pas de troisième issue.")


def test_the_films_carry_the_phrases_and_the_rule_that_holds_them() -> None:
    """Two halves, each useless alone: spans without ``inline-block`` are
    ordinary text, and the rule without spans styles nothing."""
    page = ROOT / "brag-output/films/publish-fr-portrait/index.html"
    if not page.is_file():
        pytest.skip("films not built in this checkout")
    html = page.read_text(encoding="utf-8")
    assert '<span class="ph">' in html
    assert re.search(r"\.ph\s*\{\s*display:\s*inline-block", html)
