#!/usr/bin/env python3
"""
make_brick_diagram
==================

Draw the "how it works" figure that opens each brick's ``README.md`` and
``LISEZMOI.md``.

Why this lives in the hub
-------------------------
Ten bricks, one shape. The figure says the same thing about every one of
them: here is what you hand it, here are the two things it does with that,
here is what you end up with. The suite's whole architectural claim is that
a brick **makes** and **audits**, so the drawing is built out of two lanes
rather than a single pipeline, and a reader who has seen one of the ten can
read the other nine without being taught again.

A generator per brick would have produced ten dialects of that shape within
a month. This repository is the only place that sees all ten at once (the
reason ``scripts/fetch_siblings.sh`` exists), so the renderer lives here and
the **content** lives in the brick, at ``assets/how-it-works.yaml``: the
brick owns what is true about itself, the hub owns how it is drawn.

Not a 168th chart kind
----------------------
``sprezzature-figures`` ships 167 chart kinds and that number is claimed on
the website, in the films, and in several guards. A flow diagram is not a
chart of data anyway: it has no scale and no encoding. So this is a figure
written in the house style, not a catalogue entry.

House style, kept
-----------------
* Palette and ink from ``sprezzature-colors`` through
  ``sprezzature-figures/scripts/_style.py``, the same source every
  generator reads.
* ``role="img"`` plus a ``<title>``/``<desc>`` pair, so the drawing has an
  accessible name and a description a screen reader can read out.
* An additive ``@media (prefers-color-scheme: dark)`` block, the pattern
  ``_style.os_dark_style`` established: the light render is unchanged and
  the dark one only applies when the reader's system asks for it.
* Every box width is measured with ``_textfit.text_width``, the calibrated
  Roboto advance table, never counted in characters. French runs 15 to 30
  per cent longer than the English it replaces, which is exactly the case a
  character count gets wrong.

Fonts are **not** embedded. ``_svg.svg_open`` offers that, and it costs
438 KB per file: the twenty-two figures would have added 9.6 MB of base64
Roboto to eleven repositories to control the typography of a drawing that
GitHub renders at 880 pixels wide. The stack falls back to Helvetica and Arial, whose
advances run a little wider than Roboto's, so every box carries slack.

Usage
-----
::

    # Redraw every brick, both languages
    python scripts/make_brick_diagram.py --all

    # One brick
    python scripts/make_brick_diagram.py sprezzature-colors

    # Say what would change without writing (exit 1 if anything would)
    python scripts/make_brick_diagram.py --all --check

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from skills_manifest import SHIPPED_SKILLS  # noqa: E402

#: Every folder that carries a figure: the ten bricks, plus this repository.
#: The hub is not in ``SKILLS.txt`` (that file lists what gets released as a
#: skill), and its README opens with the same drawing for the same reason, so
#: ``--all`` has to mean eleven rather than ten.
DIAGRAMMED = (*SHIPPED_SKILLS, "sprezzature")


# ------------------------------------------------------------------
# Reach the figures helpers.
#
# ``_textfit`` and ``_style`` live in ``sprezzature-figures/scripts/`` and are
# mapped to the ``sprezzature_figures_scripts`` distribution once installed.
# ``sprezzature_figures._textfit_bridge`` already solved that both-ways import,
# so this borrows its resolution rather than repeating it, then pulls the two
# modules by name. Re-implementing the measurement here is what the comment in
# ``_textfit`` warns against: a second advance table drifts from the first and
# only a clipped glyph tells you.
# ------------------------------------------------------------------
def _figures_script(name: str) -> Any:
    """Import a module from ``sprezzature-figures/scripts`` under either layout.

    Parameters
    ----------
    name : str
        Bare module name, e.g. ``"_style"``.

    Returns
    -------
    module
        The imported module.

    Raises
    ------
    SystemExit
        When ``sprezzature-figures`` is not importable at all, with the
        install line that fixes it. A diagram generator that silently
        guessed its text widths would be worse than one that stops.
    """
    try:
        import sprezzature_figures._textfit_bridge  # noqa: F401
    except ModuleNotFoundError:
        sys.exit(
            "make_brick_diagram needs sprezzature-figures for the house palette "
            "and the Roboto advance table.\n  pip install sprezzature-figures"
        )
    try:
        return importlib.import_module(f"sprezzature_figures_scripts.{name}")
    except ModuleNotFoundError:
        return importlib.import_module(name)


_style = _figures_script("_style")
_textfit = _figures_script("_textfit")
_svg = _figures_script("_svg")

text_width = _textfit.text_width
wrap_to_width = _textfit.wrap_to_width
xml_escape = _svg.xml_escape


# ------------------------------------------------------------------
# Geometry. The canvas is 980 wide because that is roughly the width of
# GitHub's content column: a drawing laid out much wider is scaled down, and
# 14 px notes stop being readable somewhere around 1400.
# ------------------------------------------------------------------
W = 980
PAD = 36
LANE_GAP = 36
LANE_W = (W - 2 * PAD - LANE_GAP) // 2
FULL_W = W - 2 * PAD

BOX_PAD_X = 18
BOX_PAD_Y = 13
BOX_RX = 12

#: Every budget handed to the wrapper is divided by this before use.
#:
#: ``text_width`` is calibrated to Roboto, and these figures are not allowed
#: to embed Roboto: the faces cost 438 KB per file and the drawing is read at
#: 880 pixels wide. So the text is actually set in whatever the reader's
#: machine offers first, and that face is wider. Measured here against the
#: stack's own fallbacks, Helvetica and Arial run 3.3 per cent over the
#: estimate on a long line; a Linux reader with only DejaVu Sans is wider
#: again. 1.09 keeps the longest line about five per cent clear of the box
#: edge on Helvetica, and still inside the padding on DejaVu.
#:
#: The number is measured, not chosen: render a line, trim the raster, divide
#: by ``text_width``. Guessing it is how a caption ends up running off both
#: edges of a canvas while every check still passes.
SLACK = 1.09

TITLE_SIZE = 28
SUB_SIZE = 16
LANE_SIZE = 15
LABEL_SIZE = 16
NOTE_SIZE = 13.5
FOOT_SIZE = 13.5

TITLE_LH = 34
SUB_LH = 22
LABEL_LH = 20
NOTE_LH = 17.5

ARROW_H = 26
STEP_GAP = 16
BAR_W = 5

#: Role colours, the same ten figures over. Blue and orange are the
#: colour-vision-safe pair: no deficiency collapses them into each other. The
#: outcome box takes no hue at all, because its role is already carried by
#: being the last thing on the page and by what it says.
INPUT_HUE = "#8E8E93"
LANE_HUES = ("#007AFF", "#FF9500")
LANE_TINTS = ("#CCE4FF", "#FFEACC")
RULE = "#C7C7CC"

INK = _style.INK
SECONDARY = _style.SECONDARY
BG = _style.BG

FONT_STACK = "Roboto, Helvetica Neue, Helvetica, Arial, sans-serif"


def _mix(hexv: str, onto: str, alpha: float) -> str:
    """Blend ``hexv`` over ``onto`` at ``alpha`` and return a hex string.

    Used for the dark-mode counterpart of a lane's pale header tint. The
    light tints come from the palette; their dark twins do not exist there,
    and picking them by eye across ten figures would have produced ten
    slightly different greys.

    Parameters
    ----------
    hexv, onto : str
        ``#RRGGBB`` strings: the hue, and the surface it sits on.
    alpha : float
        Weight of ``hexv`` in the blend, in ``[0, 1]``.

    Returns
    -------
    str
        The blended ``#RRGGBB``.
    """
    a = _svg.hex_to_rgb(hexv)
    b = _svg.hex_to_rgb(onto)
    out = tuple(round(a[i] * alpha + b[i] * (1 - alpha)) for i in range(3))
    return "#%02X%02X%02X" % out


#: Dark surface and its box fill, matching what the catalogue's own figures use.
DARK_PAPER = "#0B0B0C"
DARK_BOX = "#141416"


# ------------------------------------------------------------------
# Text blocks
# ------------------------------------------------------------------
def _lines(text: str, max_px: float, size: float, *, bold: bool = False) -> List[str]:
    """Wrap ``text`` to ``max_px`` at ``size``, honouring the house orphan rule.

    Parameters
    ----------
    text : str
        The string to wrap. Empty returns an empty list, so a box with no
        note costs no height.
    max_px : float
        Pixel budget for one line.
    size : float
        Font size the text will be drawn at.
    bold : bool, optional
        Whether the text is drawn bold, which measures about 3 per cent wider.

    Returns
    -------
    list of str
        One entry per rendered line.
    """
    if not text:
        return []
    budget = max_px / SLACK
    lines = wrap_to_width(text, budget, size, bold=bold)
    # A word wider than the budget is kept whole by the wrapper rather than
    # broken, which is right, and then it hangs out past the box edge, which
    # is not. Nothing downstream notices: the SVG is valid, the auditors pass,
    # and only a reader sees it. Fail here, naming the word.
    for line in lines:
        if len(line.split()) == 1 and text_width(line, size, bold=bold) > budget:
            raise ValueError(
                f"{line!r} is wider than the {budget:.0f} px it has to fit in "
                f"at {size:g} px. Shorten it, or split it."
            )
    return lines


def _text_el(
    x: float,
    y: float,
    lines: Sequence[str],
    size: float,
    line_height: float,
    fill: str,
    *,
    weight: str = "400",
) -> Tuple[str, float]:
    """Emit one ``<text>`` per line and return the markup and the height used.

    Parameters
    ----------
    x, y : float
        Left edge, and the baseline of the first line.
    lines : sequence of str
        Already-wrapped lines.
    size, line_height : float
        Font size, and the distance between baselines.
    fill : str
        Text colour. The dark block keys off this exact hex.
    weight : str, optional
        ``font-weight`` attribute value.

    Returns
    -------
    tuple of (str, float)
        The markup, and the vertical space consumed.
    """
    out = []
    for i, line in enumerate(lines):
        out.append(
            f'<text x="{x:.0f}" y="{y + i * line_height:.0f}" font-size="{size:g}" '
            f'font-weight="{weight}" fill="{fill}">{xml_escape(line)}</text>'
        )
    return "".join(out), len(lines) * line_height


# ------------------------------------------------------------------
# Boxes
# ------------------------------------------------------------------
def _box_height(label_lines: int, note_lines: int) -> float:
    """Height of a box holding ``label_lines`` bold lines and ``note_lines`` notes."""
    h: float = 2 * BOX_PAD_Y + label_lines * LABEL_LH
    if note_lines:
        h += 4 + note_lines * NOTE_LH
    return h


def _box(
    x: float,
    y: float,
    w: float,
    label: str,
    note: str,
    *,
    stroke: str,
    dashed: bool = False,
    bar: str = "",
) -> Tuple[str, float]:
    """Draw one box and return its markup and its height.

    Parameters
    ----------
    x, y, w : float
        Top-left corner and width.
    label : str
        The bold line, what the stage is.
    note : str
        The grey line under it, how it does it. May be empty.
    stroke : str
        Border colour.
    dashed : bool, optional
        Dashed border. Reserved for the input box, so that "what you hand
        it" is distinguishable from "what it does" without reading a colour.
    bar : str, optional
        Hex of a filled bar down the inside of the left edge. Marks a result
        box, again as a second channel beside the hue.

    Returns
    -------
    tuple of (str, float)
        Markup, and the height the box occupies.
    """
    inner_x = x + BOX_PAD_X + (BAR_W + 6 if bar else 0)
    inner_w = w - 2 * BOX_PAD_X - (BAR_W + 6 if bar else 0)
    label_lines = _lines(label, inner_w, LABEL_SIZE, bold=True)
    note_lines = _lines(note, inner_w, NOTE_SIZE)
    h = _box_height(len(label_lines), len(note_lines))

    dash = ' stroke-dasharray="6 5"' if dashed else ""
    parts = [
        f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" '
        f'rx="{BOX_RX}" fill="{BG}" stroke="{stroke}" stroke-width="1.6"{dash}/>'
    ]
    if bar:
        parts.append(
            f'<path d="M{x + 1.6:.0f},{y + BOX_RX:.0f} '
            f'v{h - 2 * BOX_RX:.0f}" stroke="{bar}" stroke-width="{BAR_W}" '
            f'stroke-linecap="round" fill="none"/>'
        )

    cursor = y + BOX_PAD_Y + LABEL_SIZE
    markup, used = _text_el(inner_x, cursor, label_lines, LABEL_SIZE, LABEL_LH, INK, weight="600")
    parts.append(markup)
    if note_lines:
        cursor += used + 4
        markup, _ = _text_el(inner_x, cursor, note_lines, NOTE_SIZE, NOTE_LH, SECONDARY)
        parts.append(markup)
    return "".join(parts), h


def _arrow(cx: float, y: float, height: float = ARROW_H) -> str:
    """A short vertical connector with a head, from ``y`` down ``height``."""
    return (
        f'<path d="M{cx:.0f},{y:.0f} v{height - 7:.0f}" stroke="{RULE}" '
        f'stroke-width="1.6" fill="none"/>'
        f'<path d="M{cx - 4.5:.0f},{y + height - 8:.0f} L{cx:.0f},{y + height:.0f} '
        f'L{cx + 4.5:.0f},{y + height - 8:.0f}" fill="{RULE}"/>'
    )


def _elbow(x0: float, y0: float, x1: float, y1: float) -> str:
    """Connector that drops from ``(x0, y0)``, turns, and arrives at ``(x1, y1)``."""
    mid = y0 + (y1 - y0) / 2
    return (
        f'<path d="M{x0:.0f},{y0:.0f} V{mid:.0f} H{x1:.0f} V{y1 - 8:.0f}" '
        f'stroke="{RULE}" stroke-width="1.6" fill="none"/>'
        f'<path d="M{x1 - 4.5:.0f},{y1 - 8:.0f} L{x1:.0f},{y1:.0f} '
        f'L{x1 + 4.5:.0f},{y1 - 8:.0f}" fill="{RULE}"/>'
    )


# ------------------------------------------------------------------
# The figure
# ------------------------------------------------------------------
def render(spec: Dict[str, Any], lang: str) -> str:
    """Render one brick's figure, in one language.

    Parameters
    ----------
    spec : dict
        The parsed ``assets/how-it-works.yaml``. Language-specific content
        sits under the language key; everything else is shared.
    lang : {"en", "fr"}
        Which half of the spec to draw.

    Returns
    -------
    str
        A complete SVG document.
    """
    s = spec[lang]
    lanes = s["lanes"]
    if len(lanes) != 2:
        raise ValueError(f"{spec['package']} ({lang}): a figure holds exactly two lanes")

    title_lines = _lines(s["title"], FULL_W, TITLE_SIZE, bold=True)
    sub_lines = _lines(s["subtitle"], FULL_W, SUB_SIZE)

    # Floats throughout: the line heights are fractional, and an int cursor
    # would quietly round every baseline in the figure.
    y: float = 24 + TITLE_SIZE
    head: List[str] = []
    markup, used = _text_el(PAD, y, title_lines, TITLE_SIZE, TITLE_LH, INK, weight="700")
    head.append(markup)
    y += used - TITLE_LH + 12 + SUB_SIZE
    markup, used = _text_el(PAD, y, sub_lines, SUB_SIZE, SUB_LH, SECONDARY)
    head.append(markup)
    y += used - SUB_LH + 24

    body: List[str] = []

    # ---- what you hand it ----
    markup, h = _box(PAD, y, FULL_W, s["input"]["label"], s["input"].get("note", ""),
                     stroke=INPUT_HUE, dashed=True)
    body.append(markup)
    input_bottom: float = y + h
    y = input_bottom

    lane_x = (PAD, PAD + LANE_W + LANE_GAP)
    for i in range(2):
        body.append(_elbow(PAD + FULL_W / 2, input_bottom,
                           lane_x[i] + LANE_W / 2, y + ARROW_H + 14))
    y += ARROW_H + 14

    # ---- the two lanes, measured first so their results share a baseline ----
    lane_blocks: List[List[Tuple[str, float]]] = []
    for i, lane in enumerate(lanes):
        blocks: List[Tuple[str, float]] = []
        hue = LANE_HUES[i]
        for step in lane["steps"]:
            blocks.append(("step", _box_height(
                len(_lines(step["label"], LANE_W - 2 * BOX_PAD_X, LABEL_SIZE, bold=True)),
                len(_lines(step.get("note", ""), LANE_W - 2 * BOX_PAD_X, NOTE_SIZE)),
            )))
        inner = LANE_W - 2 * BOX_PAD_X - BAR_W - 6
        blocks.append(("result", _box_height(
            len(_lines(lane["result"]["label"], inner, LABEL_SIZE, bold=True)),
            len(_lines(lane["result"].get("note", ""), inner, NOTE_SIZE)),
        )))
        del hue
        lane_blocks.append(blocks)

    header_h = 30
    def lane_height(blocks: List[Tuple[str, float]]) -> float:
        return header_h + sum(b[1] for b in blocks) + STEP_GAP * len(blocks)

    tallest = max(lane_height(b) for b in lane_blocks)

    lane_bottom: float = y
    for i, lane in enumerate(lanes):
        x = lane_x[i]
        hue, tint = LANE_HUES[i], LANE_TINTS[i]
        cy: float = y
        # Lane header: a tinted strip with a hue bar, so the lane is named
        # rather than only coloured.
        head_lines = _lines(lane["title"], LANE_W - 2 * BOX_PAD_X - 10, LANE_SIZE, bold=True)
        hh = max(header_h, 10 + len(head_lines) * LABEL_LH)
        body.append(
            f'<rect x="{x:.0f}" y="{cy:.0f}" width="{LANE_W}" height="{hh:.0f}" '
            f'rx="{BOX_RX}" fill="{tint}"/>'
            f'<path d="M{x + 1.6:.0f},{cy + 8:.0f} v{hh - 16:.0f}" stroke="{hue}" '
            f'stroke-width="{BAR_W}" stroke-linecap="round" fill="none"/>'
        )
        markup, _ = _text_el(x + BOX_PAD_X + 10, cy + hh / 2 + LANE_SIZE / 2 - 2,
                             head_lines, LANE_SIZE, LABEL_LH, INK, weight="700")
        body.append(markup)
        cy += hh + STEP_GAP

        for j, step in enumerate(lane["steps"]):
            markup, h = _box(x, cy, LANE_W, step["label"], step.get("note", ""), stroke=hue)
            body.append(markup)
            cy += h
            body.append(_arrow(x + LANE_W / 2, cy, STEP_GAP + 8))
            cy += STEP_GAP + 8
            del j

        # The shorter lane carries its slack here, just above its result, so
        # both lanes start together and both finish on the same line. A ragged
        # bottom reads as a mistake; one visible gap reads as a lane that does
        # less, which is the true thing.
        cy += tallest - lane_height(lane_blocks[i])

        markup, h = _box(x, cy, LANE_W, lane["result"]["label"],
                         lane["result"].get("note", ""), stroke=hue, bar=hue)
        body.append(markup)
        cy += h
        lane_bottom = max(lane_bottom, cy)

    y = lane_bottom

    # ---- the thing you end up with, when both lanes meet in one ----
    outcome = s.get("outcome")
    if outcome:
        target_y = y + ARROW_H + 16
        for i in range(2):
            body.append(_elbow(lane_x[i] + LANE_W / 2, y, PAD + FULL_W / 2, target_y))
        y = target_y
        inner = FULL_W - 2 * BOX_PAD_X - BAR_W - 6
        del inner
        markup, h = _box(PAD, y, FULL_W, outcome["label"], outcome.get("note", ""),
                         stroke=INK, bar=INK)
        body.append(markup)
        y += h

    # ---- the line under the drawing ----
    foot_lines = _lines(s["footer"], FULL_W, FOOT_SIZE)
    y += 26
    markup, used = _text_el(PAD, y, foot_lines, FOOT_SIZE, NOTE_LH, SECONDARY)
    body.append(markup)
    y += used - NOTE_LH

    height = int(y + PAD)

    slug = spec["package"].replace("sprezzature-", "")
    tid, did = f"{slug}-hiw-title", f"{slug}-hiw-desc"

    dark = (
        "@media (prefers-color-scheme: dark){"
        f'rect[fill="{BG}"]{{fill:{DARK_BOX};}}'
        f"rect.paper{{fill:{DARK_PAPER};}}"
        f'[fill="{INK}"]{{fill:#F2F2F7;}}'
        f'[fill="{SECONDARY}"]{{fill:#9C9CA3;}}'
        f'[stroke="{INK}"]{{stroke:#F2F2F7;}}'
        f'[stroke="{RULE}"]{{stroke:#5A5A5E;}}'
        f'[fill="{RULE}"]{{fill:#5A5A5E;}}'
        + "".join(
            f'rect[fill="{LANE_TINTS[i]}"]{{fill:{_mix(LANE_HUES[i], DARK_PAPER, 0.24)};}}'
            for i in range(2)
        )
        + "}"
    )

    return (
        _svg.svg_open(W, height, tid, did, font_family=FONT_STACK, embed_fonts=False)
        + f'<title id="{tid}">{xml_escape(s["title"])}</title>'
        + f'<desc id="{did}">{xml_escape(s["alt"])}</desc>'
        + f"<style>{dark}</style>"
        + f'<rect class="paper" width="{W}" height="{height}" fill="{BG}"/>'
        + "".join(head)
        + "".join(body)
        + "</svg>\n"
    )


# ------------------------------------------------------------------
# Files
# ------------------------------------------------------------------
#: Output name per language. The French file is named in French: a reader
#: who lands on ``LISEZMOI.md`` and follows the image URL should not be
#: handed an English filename.
OUT_NAME = {"en": "how-it-works.svg", "fr": "comment-ca-marche.svg"}

SPEC_NAME = "how-it-works.yaml"


def brick_root(brick: str) -> Path:
    """Path of a brick checkout, beside this repository.

    ``"sprezzature"`` resolves to this checkout itself rather than to a
    sibling of the same name. A runner clones the hub into a directory named
    after the repository, so ``parent / "sprezzature"`` would be this very
    folder on CI and a different one on a developer machine that keeps its
    checkout under another name. Naming it outright removes the question.
    """
    if brick == "sprezzature":
        return REPO_ROOT
    return REPO_ROOT.parent / brick


def spec_path(brick: str) -> Path:
    """Path of a brick's figure specification."""
    return brick_root(brick) / "assets" / SPEC_NAME


def out_path(brick: str, lang: str) -> Path:
    """Path of a brick's rendered figure, in one language."""
    return brick_root(brick) / "assets" / OUT_NAME[lang]


def load_spec(brick: str) -> Dict[str, Any]:
    """Read and lightly validate one brick's specification.

    Parameters
    ----------
    brick : str
        Folder name, e.g. ``"sprezzature-maps"``.

    Returns
    -------
    dict
        The parsed specification.

    Raises
    ------
    ValueError
        When a language half is missing a key the renderer needs. Failing
        here names the file and the key; failing inside the renderer would
        name a line number in this script.
    """
    spec = yaml.safe_load(spec_path(brick).read_text(encoding="utf-8"))
    for lang in ("en", "fr"):
        if lang not in spec:
            raise ValueError(f"{spec_path(brick)}: no '{lang}' half")
        for key in ("title", "subtitle", "alt", "footer", "input", "lanes"):
            if key not in spec[lang]:
                raise ValueError(f"{spec_path(brick)}: {lang} has no '{key}'")
    return spec


def main(argv: Sequence[str] | None = None) -> int:
    """Command line. Returns a process exit code."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[2])
    ap.add_argument("brick", nargs="*", help="folder names; default is every one")
    ap.add_argument("--all", action="store_true", help="the ten bricks and this repository")
    ap.add_argument(
        "--check",
        action="store_true",
        help="do not write; exit 1 if any committed figure differs from a fresh render",
    )
    args = ap.parse_args(argv)

    bricks = list(args.brick) or (list(DIAGRAMMED) if args.all else [])
    if not bricks:
        ap.error("name a brick, or pass --all")

    stale: List[str] = []
    for brick in bricks:
        if not spec_path(brick).exists():
            print(f"  {brick}: no assets/{SPEC_NAME}, skipped")
            continue
        spec = load_spec(brick)
        for lang in ("en", "fr"):
            svg = render(spec, lang)
            dest = out_path(brick, lang)
            if args.check:
                current = dest.read_text(encoding="utf-8") if dest.exists() else ""
                if current != svg:
                    stale.append(str(dest))
                continue
            dest.write_text(svg, encoding="utf-8")
            print(f"  {dest.relative_to(REPO_ROOT.parent)}  {len(svg) // 1024} KB")

    if stale:
        print("stale, re-run without --check:\n  " + "\n  ".join(stale))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
