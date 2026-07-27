#!/usr/bin/env python3
"""
make_waffle — a house-styled waffle chart (square pie) as a hand-authored SVG.

A waffle chart lays out a 10x10 grid of 100 unit squares and fills a
run of squares per category so that the *count of squares* reads off
the proportion directly — one square is one percent. It is the
part-to-whole alternative to a pie: easier to compare small shares,
and it never asks the eye to judge angles.

This module builds the SVG string by hand (no matplotlib / seaborn /
plotly, and no Vega here because a fixed 10x10 glyph grid is clearer
authored directly). It follows the front-* house style pulled from
:mod:`_style`: the Apple-ish saturated palette, Roboto typography,
ink ``#1D1D1F`` on a white background, rounded-corner tiles, a
takeaway title, and a one-line subtitle.

The figure is interactive without any JavaScript: hovering or
keyboard-focusing a legend entry or any tile of a category dims the
other categories so a single share stands out, and every tile group
carries a native ``<title>`` tooltip. Motion is guarded by
``prefers-reduced-motion``.

Six categorical hues cannot all stay distinct once colour is removed
(colour-vision deficiency or plain greyscale), so colour is never the
only key: every category carries a numbered badge (1..6) stamped on the
first tile of its run and repeated in the legend. A reader who cannot
tell the hues apart still maps a tile to its number, and the number to
the legend entry.

Running the module writes the SVG artifact to
``sprezzature-figures/assets/svg-examples/waffle.svg``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List

# The house-style palette lives in _style (stdlib-only, safe to import
# without the dataviz tier).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _svg import svg_open, xml_escape  # noqa: E402
from _render import svg_example_path, write_svg  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402


# ------------------------------------------------------------------
# Geometry + house-style constants
# ------------------------------------------------------------------
#: Canvas size, in user-space pixels. Poster-scale so the grid reads
#: comfortably at a glance and never feels cramped in the gallery.
_WIDTH: int = 1000
_HEIGHT: int = 740

#: The waffle grid is always 10x10 = 100 unit squares (one square = 1 %).
_COLS: int = 10
_ROWS: int = 10

#: Tile size and gap, in pixels.
_TILE: float = 46.0
_GAP: float = 10.0

#: Grid origin (top-left of the first tile).
_ORIGIN_X: float = 56.0
_ORIGIN_Y: float = 152.0

#: House-style inks.
_INK: str = "#1D1D1F"       # primary text
_SUBTLE: str = "#6E6E73"    # secondary text
_EMPTY: str = "#E5E5EA"     # unfilled / "remainder" tiles
_BG: str = "#FFFFFF"        # background
_FOCUS: str = "#0A4DA0"     # focus-ring blue


def _dataset(accessibility: str = "universal") -> List[Dict[str, object]]:
    """Return the communicative fake data for the waffle.

    A household-energy budget: of every 100 kilowatt-hours a typical
    all-electric home draws in a year, how many go to each end use.
    The shares sum to 100 so the grid fills exactly.

    Parameters
    ----------
    accessibility : str, optional
        Palette accessibility level threaded to :func:`load_palette`
        (``"universal"``, ``"high-contrast"``, ``"monochrome"``,
        ``"deuteranopia"``, ``"protanopia"`` or ``"tritanopia"``). Defaults
        to ``"universal"``, the colour-vision-safe standard.

    Returns
    -------
    list of dict
        One dict per category with ``label`` (str), ``value`` (int
        squares / percent), and ``color`` (hex) keys, largest first.
    """
    palette = load_palette(accessibility)
    # Ordered largest -> smallest so the fill sweeps the grid tidily and
    # the legend reads top-down by size.
    rows = [
        ("Heating & cooling", 34, "Red"),
        ("Water heating", 18, "Orange"),
        ("Appliances & plug loads", 16, "Blue"),
        ("Electric vehicle", 14, "Purple"),
        ("Lighting", 9, "Yellow"),
        ("Cooking", 9, "Turquoise"),
    ]
    return [
        {"label": label, "value": value, "color": palette[color]}
        for label, value, color in rows
    ]


def _slug(label: str) -> str:
    """Turn a category label into a CSS-class-safe slug."""
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in label).strip("-")


# Local alias for the shared escape helper; call sites keep the _xml name.
_xml = xml_escape


def build_svg(mode: str = "self-contained", accessibility: str = "universal") -> str:
    """Assemble the full waffle-chart SVG document as a string.

    Parameters
    ----------
    mode : str, optional
        Interactivity mode for the fullscreen control, one of three:
        ``"self-contained"`` (default) ships a self-carrying fullscreen
        button plus its wiring script; ``"external"`` ships no button and
        defers fullscreen to a page-level module; ``"static"`` ships no
        interactivity at all.
    accessibility : str, optional
        Palette accessibility level (``"universal"``, ``"high-contrast"``,
        ``"monochrome"``, ``"deuteranopia"``, ``"protanopia"`` or
        ``"tritanopia"``). Defaults to ``"universal"``, the
        colour-vision-safe standard, which leaves the shipped palette
        unchanged.

    Returns
    -------
    str
        A complete, standalone SVG document.
    """
    data = _dataset(accessibility)
    total = sum(int(d["value"]) for d in data)  # noqa: F841  (documents the 100 invariant)

    # Map each of the 100 grid cells (filled column-by-column, bottom-up
    # so the largest share grows from the floor like a stacked column) to
    # a category slug, or None for the remainder.
    cell_owner: List[str] = []
    for d in data:
        cell_owner.extend([_slug(str(d["label"]))] * int(d["value"]))
    cell_owner.extend([""] * (_COLS * _ROWS - len(cell_owner)))

    color_of = {_slug(str(d["label"])): str(d["color"]) for d in data}

    # ---- header ----
    parts: List[str] = []
    parts.append(svg_open(_WIDTH, _HEIGHT, "wf-title", "wf-desc"))
    parts.append(
        '<title id="wf-title">Where a home’s electricity goes, '
        'per 100 kilowatt-hours</title>'
    )
    desc = (
        "Waffle chart: a 10 by 10 grid of 100 squares, one square per "
        "percent of annual household electricity use. "
        + "; ".join(f"{_xml(str(d['label']))} {d['value']}" for d in data)
        + ". Heating and cooling dominate at 34 squares."
    )
    parts.append(f'<desc id="wf-desc">{desc}</desc>')

    # ---- interactivity + house style (pure CSS, no JS) ----
    style_rows = [
        ".tile { transition: opacity .18s ease; }",
        # Hover/focus any category (a tile or its legend swatch) dims the rest.
        "svg:hover .cat, svg:focus-within .cat { opacity: .28; }",
    ]
    for d in data:
        s = _slug(str(d["label"]))
        # When THIS category is hovered/focused (anywhere in its group),
        # restore its own opacity to full.
        style_rows.append(
            f".cat-{s}:hover .cat-{s}, .cat-{s}:focus .cat-{s}, "
            f".cat-{s}:hover, .cat-{s}:focus {{ opacity: 1; }}"
        )
    style_rows.extend([
        ".legend-row { cursor: pointer; }",
        f".legend-row:focus {{ outline: 3px solid {_FOCUS}; outline-offset: 2px; }}",
        "@media (prefers-reduced-motion: reduce) { .tile { transition: none; } }",
    ])
    # OS-adaptive overrides (additive; the default render stays byte-identical
    # because every rule below lives inside a media query). Under
    # prefers-contrast the six end-use hues deepen to their high-contrast
    # values on the tiles and legend swatches. Under forced colours the tiles
    # hand off to the system palette — legitimate here because every category
    # already carries a colour-free key (a 1..6 badge on its first tile and in
    # the legend) plus its run position, so identity survives with no colour.
    # The empty-tile hue is deliberately left out (it is a neutral remainder,
    # not a category), and the white badge discs stay put so the numbers keep
    # reading over the now-system fills.
    cat_series = {f"rect.cat-{_slug(str(d['label']))}": str(d["color"]) for d in data}
    style_rows.append(os_adaptive_style(cat_series, role="fill", forced=True))
    # Additive OS dark-mode block. The white page darkens and the ink tiers flip
    # to light via the ink-map default; that same flip turns each white badge
    # disc into a dark disc and its ink number into a light number, so the 1..6
    # badges keep reading as a light glyph on a dark disc over the saturated
    # tile. The light-grey remainder tiles (#E5E5EA) darken to a quiet grey so
    # they sit back on the dark page. Category hues are data and left alone.
    style_rows.append(
        os_dark_style(
            screen_blend=False,
            extra='[fill="#E5E5EA"]{fill:#2A2A2C;}',
        )
    )
    parts.append("<style>\n" + "\n".join(style_rows) + "\n</style>")

    # ---- background ----
    parts.append(f'<rect width="{_WIDTH}" height="{_HEIGHT}" fill="{_BG}"/>')

    # ---- title + subtitle ----
    parts.append(
        f'<text x="{_ORIGIN_X}" y="66" font-size="30" font-weight="700" '
        f'fill="{_INK}">Heating &amp; cooling eats a third of home power</text>'
    )
    parts.append(
        f'<text x="{_ORIGIN_X}" y="102" font-size="18" fill="{_SUBTLE}">'
        f'Share of annual household electricity use · one square = 1 % '
        f'· illustrative</text>'
    )

    # ---- waffle grid ----
    # Group tiles by category so one CSS rule dims/highlights a whole share.
    # Emit the remainder (empty) tiles first, then one <g> per category.
    def _cell_xy(idx: int) -> tuple[float, float]:
        """Column-major, bottom-up placement of cell ``idx`` in the grid."""
        col = idx // _ROWS
        row_from_bottom = idx % _ROWS
        x = _ORIGIN_X + col * (_TILE + _GAP)
        y = _ORIGIN_Y + (_ROWS - 1 - row_from_bottom) * (_TILE + _GAP)
        return x, y

    # Empty remainder tiles (none here, since shares sum to 100 — kept for
    # robustness if the dataset ever under-fills the grid).
    empty_idx = [i for i, owner in enumerate(cell_owner) if owner == ""]
    if empty_idx:
        parts.append('<g>')
        for i in empty_idx:
            x, y = _cell_xy(i)
            parts.append(
                f'<rect class="tile" x="{x:.1f}" y="{y:.1f}" '
                f'width="{_TILE}" height="{_TILE}" rx="5" fill="{_EMPTY}"/>'
            )
        parts.append('</g>')

    # A per-category number (1..6) is the colour-free key: it is stamped on
    # the first tile of each run and repeated on the legend swatch, so the
    # chart still reads under colour-vision deficiency and in pure greyscale.
    number_of = {_slug(str(d["label"])): k + 1 for k, d in enumerate(data)}

    for d in data:
        s = _slug(str(d["label"]))
        color = color_of[s]
        badge = number_of[s]
        parts.append(
            f'<g class="cat cat-{s}" tabindex="0" role="listitem">'
            f'<title>{_xml(str(d["label"]))}: {d["value"]} % '
            f'({d["value"]} squares)</title>'
        )
        first_cell = True
        for i, owner in enumerate(cell_owner):
            if owner != s:
                continue
            x, y = _cell_xy(i)
            parts.append(
                f'<rect class="tile cat-{s}" x="{x:.1f}" y="{y:.1f}" '
                f'width="{_TILE}" height="{_TILE}" rx="5" fill="{color}"/>'
            )
            if first_cell:
                # Stamp the category number on its first tile. A white disc
                # keyline lifts the numeral off any hue so it reads on the
                # dark and light tiles alike, with no black ring.
                cx = x + _TILE / 2.0
                cy = y + _TILE / 2.0
                parts.append(
                    f'<circle class="cat-{s}" cx="{cx:.1f}" cy="{cy:.1f}" '
                    f'r="14" fill="#FFFFFF" fill-opacity="0.92"/>'
                )
                parts.append(
                    f'<text class="cat-{s}" x="{cx:.1f}" y="{cy:.1f}" '
                    f'text-anchor="middle" dominant-baseline="central" '
                    f'font-size="19" font-weight="700" fill="{_INK}">{badge}</text>'
                )
                first_cell = False
        parts.append('</g>')

    # ---- legend (right of the grid) ----
    legend_x = _ORIGIN_X + _COLS * (_TILE + _GAP) + 44.0
    legend_y = _ORIGIN_Y + 8.0
    row_h = 88.0
    sw = 30.0  # legend swatch size
    parts.append(f'<g transform="translate({legend_x:.1f},{legend_y:.1f})">')
    for k, d in enumerate(data):
        s = _slug(str(d["label"]))
        color = color_of[s]
        cy = k * row_h
        parts.append(
            f'<g class="cat cat-{s} legend-row" tabindex="0" role="listitem" '
            f'transform="translate(0,{cy:.1f})">'
            f'<title>{_xml(str(d["label"]))}: {d["value"]} %</title>'
        )
        parts.append(
            f'<rect class="cat-{s}" x="0" y="0" width="{sw}" height="{sw}" '
            f'rx="7" fill="{color}"/>'
        )
        # The same number that badges this category's first tile — the
        # colour-free key that ties legend to grid under CVD / greyscale.
        parts.append(
            f'<circle class="cat-{s}" cx="{sw / 2:.1f}" cy="{sw / 2:.1f}" '
            f'r="11" fill="#FFFFFF" fill-opacity="0.92"/>'
        )
        parts.append(
            f'<text class="cat-{s}" x="{sw / 2:.1f}" y="{sw / 2:.1f}" '
            f'text-anchor="middle" dominant-baseline="central" '
            f'font-size="16" font-weight="700" fill="{_INK}">{number_of[s]}</text>'
        )
        parts.append(
            f'<text x="{sw + 18:.0f}" y="12" font-size="20" font-weight="600" '
            f'fill="{_INK}" dominant-baseline="middle">'
            f'{number_of[s]}. {_xml(str(d["label"]))}</text>'
        )
        parts.append(
            f'<text x="{sw + 18:.0f}" y="38" font-size="16" font-weight="600" '
            f'fill="{_SUBTLE}" dominant-baseline="middle">{d["value"]} %</text>'
        )
        parts.append('</g>')
    parts.append('</g>')

    parts.append(fullscreen_control(_WIDTH, _HEIGHT, mode))
    parts.append('</svg>')
    return "\n".join(parts)


def main() -> None:
    """Write the waffle SVG to the skill's ``svg-examples`` folder."""
    parser = argparse.ArgumentParser(description="Render the waffle-chart SVG.")
    parser.add_argument(
        "--mode",
        choices=("self-contained", "external", "static"),
        default="self-contained",
        help="Interactivity mode for the fullscreen control.",
    )
    parser.add_argument(
        "--accessibility",
        choices=(
            "universal",
            "high-contrast",
            "monochrome",
            "deuteranopia",
            "protanopia",
            "tritanopia",
        ),
        default="universal",
        help="Palette accessibility level (default: universal, the CVD-safe standard).",
    )
    parser.add_argument("--out", default=None, help="Output path (defaults to the example asset).")
    args = parser.parse_args()
    out = Path(args.out) if args.out else svg_example_path(__file__, "waffle")
    write_svg(out, build_svg(args.mode, args.accessibility))


if __name__ == "__main__":
    main()
