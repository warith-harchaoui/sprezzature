"""
No line of film text wraps and leaves its last word standing alone.

Ten sixty-second films were written in one sitting, and the first render of
the suite film put ``DO`` alone on a second line under ``THE PART NO REFERENCE
CAN``, ``caption`` alone under a five-item list, and ``rejected.`` alone under
a ninety-eight-character caption. None of it is an error -- the text is
correct, the contrast passes, ``hyperframes check`` is happy -- it just looks
like nobody read it back.

The class is worth a guard because of what it costs to see. A widow is only
visible *after* a render: thirty-seven seconds per film, times eleven films,
times however many formats, and then somebody has to look at the one frame
where it happens. Writing a scene takes a minute; proving the scene reads
takes most of an hour.

This measures rather than counts
--------------------------------

The first three versions of this test counted characters, and all three were
wrong, in instructive ways:

1. One width for everything. It cleared ``WCAG 1.4.2 - the page talks over
   the reader``, which wraps and orphans ``reader``.
2. A width that shrank as the panel's key column grew. Plausible, and false:
   ``.pk`` carries ``min-width: 380px``, which holds the column open under
   every key these films use, so the value column is the same width in all of
   them.
3. A tighter single width. That one flagged ``colors, audio, ux-laws,
   figures, maps, video`` -- forty-four characters that render comfortably --
   while still clearing ``a sentence, and the code that has to agree``, which
   is forty-two and does not. No character count can separate those two: one
   is full of ``i``, ``l``, ``t`` and commas, the other of ``a``, ``m``,
   ``o`` and ``d``. Roboto is proportional, and the test was not.

So it measures, with the same font the films render in. ``web/fonts/roboto``
is this repository's own copy, tracked, so this needs nothing from a sibling
checkout and never skips.

Where the column widths come from
---------------------------------

Off the stylesheet in ``build_films.py``, not off a frame:

``* { box-sizing: border-box }``, a ``.card`` 1280px wide with a 2px border
and 22px padding, a ``.prow`` that is ``display: flex`` with a 28px gap, and
a ``.pk`` holding ``min-width: 380px``. So a panel value has
``1280 - 2*2 - 2*22 - 380 - 28 = 824px`` at ``font-size: 44px``.

That number is independently bracketed by two renders: ``a sentence, and the
code that has to`` is 706px and fits, adding ``agree`` makes 827px and wraps;
``ui, cli-gui, publish, accessibility, colors,`` is 743px and fits, adding
``audio`` makes 872px and wraps. The arithmetic lands inside (820, 827).

What is not a widow
-------------------

- a **loop or cvd caption**, which renders down the narrow right-hand column
  where four short lines are the intended shape.
- a last line that is **most of the column wide**. ``Open Graph, Twitter
  Card, Schema.org`` over ``JSON-LD, drafted locally`` is a balanced break,
  and demanding otherwise would force every two-line value onto one line and
  cost facts.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "brag-output"))

FONTS = {
    "sans": ROOT / "web/fonts/roboto/Roboto-Variable.woff2",
    "mono": ROOT / "web/fonts/roboto-mono/Roboto-Mono-Variable.woff2",
}

# Pixels available, and the size the text is set at.
#
# Landscape only, and that is now a decision rather than a shortcut. The same
# caption that sits on one comfortable line at 1712px wraps three times in
# portrait, where the column is 936px and the type is larger; measured across
# both cuts of all eleven films, the social formats held 34 one-word last
# lines against none in landscape. Shortening the text to satisfy all three
# would have damaged the format the site embeds in order to tidy the two it
# does not, so the social formats are handled where the problem is — the
# stylesheet, with `text-wrap: balance` on `.caption`.
#
# That CSS is also why this test keeps a greedy wrapper while the renderer no
# longer wraps greedily. Balancing can only improve a last line relative to
# greedy, never worsen it: if the greedy model says a line does not widow,
# the balanced render certainly does not. The model stays sound in the
# direction that matters — no false negatives — and gains only the false
# alarms the module docstring already declares acceptable.
CARD, BORDER, PAD, GAP, KEY_MIN = 1280, 2, 22, 28, 380
ROW_PX = CARD - 2 * BORDER - 2 * PAD - KEY_MIN - GAP          # 824
COL_PX = 1920 - 2 * 104                                        # the stage column
LOOP_PX = 520        # the right-hand column a loop and a cvd scene share

# (pixels, font size) per place a line of text can land.
PLACE = {
    "row": (ROW_PX, 44),            # .pv  -> h2
    "caption": (COL_PX, 38),        # .cap -> body
    "eyebrow": (COL_PX, 26),        # .eyebrow
    "loop_eyebrow": (LOOP_PX, 26),
}

# A last line carrying two words or fewer, in less than this share of the
# column, is a widow. Both halves matter: "tools, skill" filling a narrow
# column reads fine, and so does one long word that fills the line.
WIDOW_WORDS = 2
WIDOW_SHARE = 0.45


@lru_cache(maxsize=4)
def _advances(kind: str) -> tuple[dict[int, int], int]:
    """Advance width per codepoint, and the font's units per em."""
    from fontTools.ttLib import TTFont

    font = TTFont(FONTS[kind])
    hmtx, cmap = font["hmtx"], font.getBestCmap()
    table = {cp: hmtx[glyph][0] for cp, glyph in cmap.items() if glyph in hmtx.metrics}
    return table, font["head"].unitsPerEm


def _width(text: str, size: int, kind: str = "sans") -> float:
    """Rendered width of *text* in pixels at *size*, ignoring kerning.

    Kerning is left out deliberately. It moves a line by a pixel or two, it
    is not what decides whether a word falls off the end, and reading the
    pair table would make this slow enough that nobody runs it.
    """
    table, upem = _advances(kind)
    fallback = table.get(ord("?"), upem // 2)
    return sum(table.get(ord(c), fallback) for c in text) / upem * size


def _wrap(text: str, px: float, size: int) -> list[str]:
    """Greedy line breaking at the same places a browser breaks."""
    lines: list[str] = []
    for word in text.split():
        if lines and _width(f"{lines[-1]} {word}", size) <= px:
            lines[-1] = f"{lines[-1]} {word}"
        else:
            lines.append(word)
    return lines


def _widow(text: str, place: str) -> str | None:
    """The orphaned tail of *text* where it renders, or None if it reads."""
    px, size = PLACE[place]
    lines = _wrap(text, px, size)
    if len(lines) < 2:
        return None
    tail = lines[-1]
    if len(tail.split()) <= WIDOW_WORDS and _width(tail, size) < px * WIDOW_SHARE:
        return tail
    return None


def _lines_of(scene: dict) -> list[tuple[str, str, str]]:
    """Every piece of text in a scene, with the place it renders into."""
    kind = scene["type"]
    out = [(row[1], "row", f"{kind} row {row[0]!r}") for row in scene.get("rows", ())]
    # A loop or cvd caption renders down the narrow right-hand column, where
    # several short lines are the design rather than a defect.
    if scene.get("caption") and kind not in ("loop", "cvd"):
        out.append((scene["caption"], "caption", f"{kind} caption"))
    if scene.get("eyebrow"):
        out.append((scene["eyebrow"],
                    "loop_eyebrow" if kind in ("loop", "cvd") else "eyebrow",
                    f"{kind} eyebrow"))
    return out


def test_the_font_this_test_measures_with_is_here() -> None:
    """Without the fonts there is no measurement, only a green tick."""
    missing = [str(p.relative_to(ROOT)) for p in FONTS.values() if not p.is_file()]
    assert not missing, (
        "the films are set in Roboto and this test measures with it; these "
        f"are not in the checkout: {missing}"
    )


def test_no_film_line_leaves_its_last_word_alone() -> None:
    """Every row, caption and eyebrow, in every cut of every minute-long film.

    Both languages, because French is not a translation layer over an English
    film — it is a cut of its own, with its own words in the same boxes, and
    French runs longer than English for the same sentence. The first French
    cut of the suite film put ``skill`` alone under ``bibliothèque, CLI, API
    HTTP, outils MCP,`` where the English fitted on one line.
    """
    pytest.importorskip("fontTools", reason="fontTools reads the advance widths")
    import build_films

    found: list[str] = []
    for film, lang in build_films.cuts():
        spec = build_films.FILMS[film]
        # The three eighteen-second group films predate one-film-per-brick and
        # are being retired; they are not re-cut, so they are not re-checked.
        if spec["duration"] < 30:
            continue
        spec = build_films.in_language(spec, lang, film)
        for i, scene in enumerate(spec["scenes"]):
            for text, place, where in _lines_of(scene):
                tail = _widow(text, place)
                if tail is not None:
                    found.append(f"{film}.{lang} scene {i} {where}: "
                                 f"...{tail!r} alone\n    {text!r}")
    assert not found, (
        f"{len(found)} line(s) wrap and leave the last word alone:\n"
        + "\n".join(found)
    )
